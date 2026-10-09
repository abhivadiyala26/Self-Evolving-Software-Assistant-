"""Focused regression tests for auth, account isolation, order retries, and recovery policy."""

import os
import asyncio
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import main
import services.database as database
from services.auth import AuthSession, User, hash_password, verify_password
from services.database import Base, Order
from services.recovery_policy import classify_recovery_risk, critical_metrics_sustained


async def _idle_worker():
    """Keep API tests independent of the background telemetry simulator."""
    import asyncio

    await asyncio.Event().wait()


class AutoSRERegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="autosre-tests-")
        cls.engine = create_engine(
            f"sqlite:///{Path(cls.temp_dir.name, 'test.db').as_posix()}",
            connect_args={"check_same_thread": False},
        )
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)
        cls.env = patch.dict(os.environ, {
            "AUTOSRE_ADMIN_EMAIL": "operator@example.test",
            "AUTOSRE_ADMIN_PASSWORD": "test-admin-password-123",
        })
        cls.env.start()
        database.engine = cls.engine
        database.SessionLocal = cls.session_factory
        main.SessionLocal = cls.session_factory
        main.DATABASE_CONFIGURED = True
        cls.simulator_patch = patch.object(main, "supervised_simulator_loop", _idle_worker)
        cls.monitor_patch = patch.object(main, "background_monitor_loop", _idle_worker)
        cls.simulator_patch.start()
        cls.monitor_patch.start()
        cls.client = TestClient(main.app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.simulator_patch.stop()
        cls.monitor_patch.stop()
        cls.engine.dispose()
        cls.env.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        with self.session_factory() as db:
            from services.auth import provision_configured_admin

            provision_configured_admin(db)
        main.database_ready = True
        main.simulator.reset()
        main.incident_manager.reset()
        main.demo_logs.clear()
        main.alerts.clear()
        main.monitor_violation_streaks.clear()
        main.monitor_metric_started.clear()
        main.processed_incidents.clear()
        main.processing_incidents.clear()
        main.recovery_in_progress.clear()
        main.runtime_generation = 0

    def register(self, email="shopper@example.test", password="customer-password-1", **extra):
        return self.client.post("/api/auth/register", json={
            "name": "Shopper",
            "email": email,
            "password": password,
            **extra,
        })

    def test_user_registration_hashes_password_and_never_grants_admin_role(self):
        response = self.register(role="admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "user")
        with self.session_factory() as db:
            user = db.scalar(select(User).where(User.email == "shopper@example.test"))
            self.assertNotEqual(user.password_hash, "customer-password-1")
            self.assertTrue(verify_password("customer-password-1", user.password_hash))

    def test_duplicate_email_is_case_insensitive(self):
        self.assertEqual(self.register().status_code, 200)
        duplicate = self.register(email="SHOPPER@EXAMPLE.TEST")
        self.assertEqual(duplicate.status_code, 409)

    def test_registration_rejects_invalid_email_and_short_password(self):
        invalid_email = self.client.post("/api/auth/register", json={"name": "X", "email": "bad", "password": "long-enough"})
        short_password = self.client.post("/api/auth/register", json={"name": "X", "email": "x@example.test", "password": "short"})
        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(short_password.status_code, 422)

    def test_admin_is_provisioned_from_environment_and_can_sign_in(self):
        response = self.client.post("/api/auth/login", json={
            "email": "operator@example.test", "password": "test-admin-password-123", "role": "admin",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "admin")
        protected = self.client.get("/api/incidents", headers={"X-Admin-Token": response.json()["token"]})
        self.assertEqual(protected.status_code, 200)

    def test_user_cannot_escalate_or_access_admin_routes(self):
        response = self.register()
        token = response.json()["token"]
        denied = self.client.get("/api/incidents", headers={"X-Auth-Token": token})
        wrong_role = self.client.post("/api/auth/login", json={
            "email": "shopper@example.test", "password": "customer-password-1", "role": "admin",
        })
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(wrong_role.status_code, 401)

    def test_session_is_stored_as_hash_and_logout_revokes_it(self):
        response = self.register()
        token = response.json()["token"]
        with self.session_factory() as db:
            session = db.scalar(select(AuthSession))
            self.assertNotEqual(session.token_hash, token)
            self.assertEqual(len(session.token_hash), 64)
        headers = {"X-Auth-Token": token}
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_invalid_credentials_do_not_authenticate(self):
        self.register()
        response = self.client.post("/api/auth/login", json={
            "email": "shopper@example.test", "password": "not-the-password", "role": "user",
        })
        self.assertEqual(response.status_code, 401)

    def test_missing_durable_storage_fails_closed(self):
        main.DATABASE_CONFIGURED = False
        main.database_ready = False
        try:
            response = self.register()
            self.assertEqual(response.status_code, 503)
            self.assertIn("storage", response.json()["detail"].lower())
        finally:
            main.DATABASE_CONFIGURED = True
            main.database_ready = True

    def test_order_requires_authentication(self):
        response = self.client.get("/api/orders")
        self.assertEqual(response.status_code, 401)

    def test_order_is_persisted_and_idempotent_retry_returns_same_order(self):
        token = self.register().json()["token"]
        headers = {"X-Auth-Token": token, "Idempotency-Key": "checkout-request-001"}
        payload = {
            "items": [{"id": "prod-book-1", "name": "Demo book", "price": 100, "quantity": 1}],
            "totalAmount": 149,
            "paymentMethod": "UPI",
            "address": "12 Main Street, Pune",
            "deliveryOption": "standard",
        }
        first = self.client.post("/api/orders", headers=headers, json=payload)
        retry = self.client.post("/api/orders", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["order"]["paymentStatus"], "payment_pending_demo")
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.json()["replayed"])
        self.assertEqual(retry.json()["order"]["order_id"], first.json()["order"]["order_id"])
        with self.session_factory() as db:
            self.assertEqual(len(list(db.scalars(select(Order)))), 1)

    def test_idempotency_key_cannot_be_reused_for_different_checkout(self):
        token = self.register().json()["token"]
        headers = {"X-Auth-Token": token, "Idempotency-Key": "checkout-request-002"}
        payload = {
            "items": [{"id": "p1", "name": "Item", "price": 100, "quantity": 1}],
            "totalAmount": 149, "paymentMethod": "CARD", "address": "12 Main Street", "deliveryOption": "standard",
        }
        self.assertEqual(self.client.post("/api/orders", headers=headers, json=payload).status_code, 200)
        payload["address"] = "99 New Street"
        self.assertEqual(self.client.post("/api/orders", headers=headers, json=payload).status_code, 409)

    def test_orders_are_private_to_the_account(self):
        first_token = self.register().json()["token"]
        payload = {
            "items": [{"id": "p1", "name": "Item", "price": 100, "quantity": 1}],
            "totalAmount": 149, "paymentMethod": "CARD", "address": "12 Main Street", "deliveryOption": "standard",
        }
        self.assertEqual(self.client.post("/api/orders", headers={"X-Auth-Token": first_token, "Idempotency-Key": "private-order-1"}, json=payload).status_code, 200)
        second_token = self.register(email="another@example.test").json()["token"]
        other_orders = self.client.get("/api/orders", headers={"X-Auth-Token": second_token})
        self.assertEqual(other_orders.status_code, 200)
        self.assertEqual(other_orders.json(), [])

    def test_recovery_risk_depends_on_action_bounds_not_incident_label(self):
        safe = classify_recovery_risk(action="restart_service", target="paymentservice", plan={}, impacted_services={"paymentservice"})
        unsafe = classify_recovery_risk(action="delete_database", target="database", plan={}, impacted_services={"database"})
        unbounded = classify_recovery_risk(action="scale_deployment", target="paymentservice", plan={"replicas": 8}, impacted_services={"paymentservice"})
        sustained_scale = classify_recovery_risk(action="scale_deployment", target="paymentservice", plan={"replicas": 4}, impacted_services={"paymentservice"}, critical_sustained=True)
        self.assertEqual(safe, "medium")
        self.assertEqual(unsafe, "critical")
        self.assertEqual(unbounded, "high")
        self.assertEqual(sustained_scale, "high")

    def test_temporary_latency_is_kept_in_monitoring_without_approval_or_scaling(self):
        main.simulator.metrics["paymentservice"].update(latency_p95_ms=450, error_rate=4)
        main.simulator.service_states["paymentservice"] = "degraded"
        incident = main.incident_manager.create_incident("payment_high_latency", "paymentservice", main.simulator.get_metrics())
        with patch.object(main, "determine_remediation", return_value={"action": "scale_deployment", "target": "paymentservice", "replicas": 4, "message": "Scale payment service"}), \
             patch.object(main, "CRITICAL_WINDOW_SECONDS", 0.01), \
             patch.object(main.asyncio, "sleep", new=AsyncMock()):
            asyncio.run(main.orchestrate_agents("payment_high_latency", incident["incident_id"], main.runtime_generation, "paymentservice"))
        result = main.incident_manager.get_incident_by_id(incident["incident_id"])
        self.assertEqual(result["status"], "monitoring")
        self.assertEqual(result["approval_status"], "not_required")
        self.assertIsNone(result["recovery_action"])
        self.assertEqual(main.simulator.replicas["paymentservice"], 2)

    def test_sustained_critical_latency_requests_approval_for_scale(self):
        main.simulator.metrics["paymentservice"].update(latency_p95_ms=900, error_rate=4)
        incident = main.incident_manager.create_incident("payment_high_latency", "paymentservice", main.simulator.get_metrics())
        main.monitor_metric_started[("paymentservice", "latency")] = time.monotonic() - 20
        with patch.object(main, "determine_remediation", return_value={"action": "scale_deployment", "target": "paymentservice", "replicas": 4, "message": "Scale payment service"}), \
             patch.object(main.asyncio, "sleep", new=AsyncMock()):
            asyncio.run(main.orchestrate_agents("payment_high_latency", incident["incident_id"], main.runtime_generation, "paymentservice"))
        result = main.incident_manager.get_incident_by_id(incident["incident_id"])
        self.assertEqual(result["status"], "awaiting_approval")
        self.assertEqual(result["approval_status"], "pending")
        self.assertEqual(result["risk_level"], "high")

    def test_simulated_recovery_only_changes_verified_targets(self):
        main.simulator.service_states["cartservice"] = "down"
        self.assertTrue(main.simulator.recover_service("paymentservice"))
        self.assertEqual(main.simulator.service_states["paymentservice"], "recovering")
        self.assertEqual(main.simulator.service_states["cartservice"], "down")
        self.assertTrue(main.simulator.complete_recovery(main.simulator.last_recovery_affected))
        self.assertEqual(main.simulator.service_states["paymentservice"], "healthy")
        self.assertEqual(main.simulator.service_states["cartservice"], "down")

    def test_critical_metrics_require_the_configured_sustained_window(self):
        metrics = {"latency_p95_ms": 750, "error_rate": 0}
        self.assertFalse(critical_metrics_sustained(metrics, latency_duration=5))
        self.assertTrue(critical_metrics_sustained(metrics, latency_duration=15))

    def test_malformed_password_hash_is_rejected(self):
        self.assertFalse(verify_password("irrelevant", "scrypt$999999999999$8$1$bad$bad"))


if __name__ == "__main__":
    unittest.main()
