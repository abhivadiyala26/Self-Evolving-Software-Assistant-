# main.py
from fastapi import FastAPI, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Import agents
from agents.monitoring_agent import detect_anomaly
from agents.analysis_agent import analyze_logs
from agents.rca_agent import root_cause
from agents.remediation_agent import determine_remediation
from agents.deployment_agent import execute_deployment
from services.boutique_simulator import simulator
from services.incident_service import incident_manager, evaluate_severity, analyze_impact
from services.auth import (
    authenticate_session,
    create_session,
    hash_password,
    normalize_email,
    public_account,
    provision_configured_admin,
    revoke_session,
    valid_email,
    verify_password,
)
from services.database import DATABASE_CONFIGURED, Order, SessionLocal, User, get_db_session, initialize_database
from services.recovery_policy import (
    AUTOMATIC_RECOVERY_ATTEMPTS,
    CRITICAL_ERROR_RATE_PERCENT,
    CRITICAL_LATENCY_MS,
    CRITICAL_WINDOW_SECONDS,
    SAFE_REPLICA_LIMIT,
    WARNING_LATENCY_MS,
    critical_metrics_sustained,
    classify_recovery_risk as policy_classify_recovery_risk,
)

app = FastAPI(title="AutoSRE Agent Backend")

DEFAULT_DEMO_FAILURE_SERVICES = ["frontend", "cartservice", "paymentservice", "productcatalogservice"]
ALLOWED_DEMO_FAILURE_SERVICES = {
    "frontend", "productcatalogservice", "cartservice", "checkoutservice", "paymentservice"
}

def _read_demo_failure_services():
    configured = os.getenv("AUTOSRE_DEMO_FAILURE_SERVICES", ",".join(DEFAULT_DEMO_FAILURE_SERVICES))
    services = list(dict.fromkeys(
        service.strip().lower()
        for service in configured.split(",")
        if service.strip().lower() in ALLOWED_DEMO_FAILURE_SERVICES
    ))
    return services if len(services) >= 3 else DEFAULT_DEMO_FAILURE_SERVICES[:]

def _read_demo_failure_count():
    try:
        configured = int(os.getenv("AUTOSRE_DEMO_FAILURE_COUNT", "4"))
    except ValueError:
        configured = 4
    return min(4, max(3, configured))

def _read_demo_seconds(name, default):
    try:
        configured = float(os.getenv(name, str(default)))
    except ValueError:
        configured = default
    return max(0.0, configured)

DEMO_FAILURE_SERVICES = _read_demo_failure_services()
DEMO_FAILURE_COUNT = min(_read_demo_failure_count(), len(DEMO_FAILURE_SERVICES))
DEMO_FAILURE_START_DELAY_SECONDS = _read_demo_seconds("AUTOSRE_DEMO_START_DELAY_SECONDS", 20)
DEMO_FAILURE_MIN_DOWN_SECONDS = _read_demo_seconds("AUTOSRE_DEMO_MIN_DOWN_SECONDS", 12)
DEMO_FAILURE_RECOVERY_PAUSE_SECONDS = _read_demo_seconds("AUTOSRE_DEMO_RECOVERY_PAUSE_SECONDS", 15)
AUTO_DEMO_FAILURES_ENABLED = os.getenv("AUTOSRE_DEMO_FAILURES_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
automatic_demo_incidents = {}
automatic_demo_crashes = {}

runtime_tasks = []
database_ready = False

@app.on_event("startup")
async def startup_event():
    global database_ready
    if DATABASE_CONFIGURED:
        try:
            initialize_database()
            database_ready = True
        except SQLAlchemyError as error:
            database_ready = False
            background_agent["last_action"] = f"Persistent storage initialization failed: {type(error).__name__}"
            add_log("System", "Storage Error", f"Persistent storage initialization failed ({type(error).__name__}); auth and orders are unavailable until storage recovers.")
        if database_ready:
            try:
                with SessionLocal() as db:
                    configured_admin = provision_configured_admin(db)
                if not configured_admin:
                    background_agent["last_action"] = "Database ready; configure AUTOSRE_ADMIN_EMAIL and AUTOSRE_ADMIN_PASSWORD to enable the admin account."
                # Continue in-progress demo order status updates after a process restart.
                with SessionLocal() as db:
                    pending_order_ids = list(db.scalars(select(Order.order_id).where(
                        Order.payment_status == "cash_on_delivery",
                        Order.status.not_in(["DELIVERED", "CANCELLED"]),
                    )))
                for order_id in pending_order_ids:
                    task = asyncio.create_task(progress_order(order_id), name=f"autosre-order-{order_id}")
                    order_progress_tasks.add(task)
                    task.add_done_callback(order_progress_tasks.discard)
                    runtime_tasks.append(task)
            except ValueError as error:
                background_agent["last_action"] = str(error)
                add_log("System", "Configuration Error", str(error))
            except SQLAlchemyError as error:
                database_ready = False
                background_agent["last_action"] = f"Account database initialization failed: {type(error).__name__}"
                add_log("System", "Storage Error", "Account database initialization failed; auth and orders are unavailable until storage recovers.")
    else:
        background_agent["last_action"] = "Durable database is not configured; configure DATABASE_URL to enable account and order persistence."

    if not any(task.get_name() in {"autosre-simulator", "autosre-monitor"} for task in runtime_tasks):
        runtime_tasks.extend([
            asyncio.create_task(supervised_simulator_loop(), name="autosre-simulator"),
            asyncio.create_task(background_monitor_loop(), name="autosre-monitor"),
        ])
        if AUTO_DEMO_FAILURES_ENABLED:
            runtime_tasks.append(asyncio.create_task(supervised_demo_failure_loop(), name="autosre-demo-failures"))
        else:
            background_agent["last_action"] = "Automatic failure demo is disabled; use the admin console to inject a scenario."

@app.on_event("shutdown")
async def shutdown_event():
    simulator.is_running = False
    for task in runtime_tasks:
        task.cancel()
    if runtime_tasks:
        await asyncio.gather(*runtime_tasks, return_exceptions=True)
    runtime_tasks.clear()

# Allow CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip().rstrip("/") for origin in os.getenv(
        "AUTOSRE_CORS_ORIGINS",
        "https://self-evolving-assistant-zeta.vercel.app,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentResponse(BaseModel):
    agent: str
    type: str
    message: str
    timestamp: str

class ChaosScenario(BaseModel):
    scenario: str = "payment_crash"
    service: str | None = None

class AdminLogin(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    role: str | None = None

class UserRegistration(BaseModel):
    name: str = Field(max_length=80)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

class OrderRequest(BaseModel):
    items: list[dict]
    totalAmount: float
    paymentMethod: str
    address: str
    deliveryOption: str = "standard"

# In-memory store for demo logs to be polled by frontend
demo_logs = []
alerts = []
order_progress_tasks = set()
current_system_state = "healthy"
runtime_generation = 0
backend_started_monotonic = time.monotonic()
background_agent = {
    "status": "starting",
    "last_cycle": None,
    "monitored_services": 0,
    "auto_recoveries": 0,
    "escalations": 0,
    "last_action": "Starting telemetry monitor",
    "activity": [],
    "demo_failures_total": DEMO_FAILURE_COUNT,
    "demo_failures_completed": 0,
    "demo_failure_current_service": None,
}
monitor_violation_streaks = {}
monitor_clear_streaks = {}
monitor_metric_started = {}
processed_incidents = set()
processing_incidents = set()
recovery_in_progress = set()

def _bearer_token(authorization: str) -> str:
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""

def require_admin(
    x_admin_token: str = Header(default=""),
    authorization: str = Header(default=""),
    db=Depends(get_db_session),
):
    if not database_ready:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable. Configure or restore the backend database.")
    token = x_admin_token or _bearer_token(authorization)
    try:
        authenticated = authenticate_session(db, token)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable.")
    if not authenticated or authenticated[0].role != "admin":
        raise HTTPException(status_code=403, detail="Admin authentication required.")
    return public_account(authenticated[0])

def require_current_user(
    x_auth_token: str = Header(default=""),
    x_admin_token: str = Header(default=""),
    authorization: str = Header(default=""),
    db=Depends(get_db_session),
):
    if not database_ready:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable. Configure or restore the backend database.")
    token = x_auth_token or x_admin_token or _bearer_token(authorization)
    try:
        authenticated = authenticate_session(db, token)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable.")
    if not authenticated:
        raise HTTPException(status_code=401, detail="Sign in to access this account.")
    return authenticated[0]

def add_log(agent: str, log_type: str, message: str):
    now = datetime.now(timezone.utc)
    lower_message = message.lower()
    service_names = list(simulator.service_states)
    service = next((name for name in service_names if name in lower_message), None)
    if not service and agent.lower() in service_names:
        service = agent.lower()
    if "fatal" in lower_message or "critical" in lower_message or "crashed" in lower_message or "critical" in log_type.lower():
        level = "CRITICAL"
    elif "error" in log_type.lower() or any(term in lower_message for term in ("error", "failed", "unavailable", "timeout", "refused")):
        level = "ERROR"
    elif "warn" in log_type.lower() or "alert" in log_type.lower() or "approval" in log_type.lower():
        level = "WARNING"
    else:
        level = "INFO"
    active_incident = incident_manager.get_active_incident()
    entry = {
        "agent": agent,
        "type": log_type,
        "level": level,
        "service": service or "AutoSRE",
        "request_id": f"req-{uuid.uuid4().hex[:10]}",
        "trace_id": f"trace-{uuid.uuid4().hex[:12]}",
        "incident_id": active_incident["incident_id"] if active_incident else None,
        "message": message,
        "timestamp": now.strftime("%I:%M:%S %p"),
        "time": now.isoformat()
    }
    demo_logs.append(entry)
    if agent not in simulator.service_states or agent in {"System", "Monitoring Agent", "Detection Agent", "Analysis", "Diagnosis Agent", "Root Cause Agent", "Recommendation Agent", "Recovery Agent", "Verification Agent", "Incident Manager Agent", "Admin"}:
        background_agent["activity"].insert(0, entry)
        del background_agent["activity"][30:]
    if len(demo_logs) > 1000:
        del demo_logs[:-1000]

def add_alert(service: str, severity: str, title: str, description: str, incident_id: str = None):
    existing = next((item for item in alerts if item.get("incident_id") == incident_id
                     and item.get("service") == service and item.get("title") == title
                     and item.get("status") == "firing"), None)
    if existing:
        return existing
    alert = {
        "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
        "service": service,
        "severity": severity,
        "title": title,
        "description": description,
        "incident_id": incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "firing"
    }
    alerts.insert(0, alert)
    del alerts[200:]
    return alert


async def background_monitor_loop():
    """Continuously evaluate telemetry and start incident work without a browser client."""
    global current_system_state
    background_agent["status"] = "running"
    while True:
        try:
            metrics = simulator.get_metrics()
            services = simulator.get_services()
            background_agent["last_cycle"] = datetime.now(timezone.utc).isoformat()
            background_agent["monitored_services"] = len(services)
            for service in services:
                name = service["id"]
                values = metrics.get(name, {})
                now_monotonic = time.monotonic()
                critical_signals = {
                    "latency": values.get("latency_p95_ms", 0) >= CRITICAL_LATENCY_MS,
                    "errors": values.get("error_rate", 0) >= CRITICAL_ERROR_RATE_PERCENT,
                    "cpu": values.get("cpu_percent", 0) >= 95,
                    "memory": values.get("memory_percent", 0) >= 97,
                    "traffic": values.get("requests_per_sec", 0) >= 1500,
                }
                sustained_critical = False
                for signal, active_signal in critical_signals.items():
                    key = (name, signal)
                    if active_signal:
                        started = monitor_metric_started.setdefault(key, now_monotonic)
                        sustained_critical = sustained_critical or now_monotonic - started >= CRITICAL_WINDOW_SECONDS
                    else:
                        monitor_metric_started.pop(key, None)
                status_breach = service["status"] != "healthy"
                violating = status_breach or sustained_critical
                monitor_violation_streaks[name] = monitor_violation_streaks.get(name, 0) + 1 if violating else 0
                fully_recovered = (
                    service["status"] == "healthy"
                    and values.get("latency_p95_ms", float("inf")) < WARNING_LATENCY_MS
                    and values.get("error_rate", float("inf")) < CRITICAL_ERROR_RATE_PERCENT
                    and values.get("cpu_percent", 100) < 95
                    and values.get("memory_percent", 100) < 97
                    and values.get("requests_per_sec", 0) < 1500
                )
                monitor_clear_streaks[name] = monitor_clear_streaks.get(name, 0) + 1 if fully_recovered else 0

            active = incident_manager.get_active_incident()
            if active and active.get("status") == "monitoring":
                incident_id = active["incident_id"]
                target = (active.get("affected_services", {}).get("directly_affected") or [None])[0]
                if target and monitor_clear_streaks.get(target, 0) >= 3:
                    incident_manager.resolve_incident(incident_id, "The temporary anomaly cleared during monitoring; no recovery action was applied.")
                    incident_manager.add_timeline_event(incident_id, "Monitoring", "Transient anomaly cleared", "The affected service and critical metrics returned to healthy values for three consecutive samples. No recovery action was needed.", "Monitoring Agent")
                    processed_incidents.discard(incident_id)
                    current_system_state = "healthy" if all(status == "healthy" for status in simulator.service_states.values()) else "anomaly"
                    add_log("Monitoring Agent", "Resolution", f"Transient anomaly for {target} cleared during observation; no recovery action was applied.")
                    active = None
                elif target and any(
                    monitor_metric_started.get((target, signal)) is not None
                    and time.monotonic() - monitor_metric_started[(target, signal)] >= CRITICAL_WINDOW_SECONDS
                    for signal in ("latency", "errors")
                ):
                    incident_manager.update_incident(incident_id, {"status": "investigating"})
                    processed_incidents.discard(incident_id)
                    add_log("Monitoring Agent", "Detection", f"Critical telemetry on {target} persisted through the observation window; resuming recovery analysis for {incident_id}.")
                    active = incident_manager.get_active_incident()
            if not active:
                candidate = next((
                    svc for svc in services
                    if (svc["status"] != "healthy" and monitor_violation_streaks.get(svc["id"], 0) >= 3)
                    or any(
                        monitor_metric_started.get((svc["id"], signal)) is not None
                        and time.monotonic() - monitor_metric_started[(svc["id"], signal)] >= CRITICAL_WINDOW_SECONDS
                        for signal in ("latency", "errors", "cpu", "memory", "traffic")
                    )
                ), None)
                if candidate:
                    name = candidate["id"]
                    current_system_state = "anomaly"
                    is_automatic_demo_crash = (
                        name == simulator.target_service
                        and simulator.chaos_scenario == "service_crash"
                        and name in automatic_demo_crashes
                    )
                    incident_scenario = "service_crash" if is_automatic_demo_crash else "telemetry_anomaly"
                    active = incident_manager.create_incident(incident_scenario, name, metrics)
                    incident_id = active["incident_id"]
                    if is_automatic_demo_crash:
                        automatic_demo_incidents[incident_id] = automatic_demo_crashes[name]
                    add_alert(name, active["severity"], f"Sustained anomaly · {name}", "Background monitor observed a sustained health or telemetry threshold breach.", incident_id)
                    add_log("Monitoring Agent", "Detection", f"Sustained telemetry anomaly detected on {name}; incident {incident_id} opened.")

            if active:
                target = (active.get("affected_services", {}).get("directly_affected") or [None])[0]
                if target and monitor_violation_streaks.get(target, 0) >= 2:
                    incident_id = active["incident_id"]
                    if incident_id not in processed_incidents and incident_id not in processing_incidents:
                        processed_incidents.add(incident_id)
                        processing_incidents.add(incident_id)
                        asyncio.create_task(orchestrate_agents(active.get("scenario", "telemetry_anomaly"), incident_id, runtime_generation, target))
        except Exception as error:
            background_agent["last_action"] = f"Monitor cycle error: {type(error).__name__}"
            add_log("Monitoring Agent", "Error", f"Background telemetry cycle failed ({type(error).__name__}).")
        await asyncio.sleep(1)

async def supervised_simulator_loop():
    while True:
        try:
            simulator.is_running = True
            await simulator.run(add_log)
            if not simulator.is_running:
                return
        except asyncio.CancelledError:
            raise
        except Exception as error:
            background_agent["last_action"] = f"Simulator worker error: {type(error).__name__}"
            add_log("System", "Worker Error", f"Simulator worker failed ({type(error).__name__}); retrying shortly.")
            await asyncio.sleep(1)

async def supervised_demo_failure_loop():
    try:
        await automatic_demo_failure_loop()
    except asyncio.CancelledError:
        raise
    except Exception as error:
        background_agent["last_action"] = f"Demo worker error: {type(error).__name__}"
        add_log("Background Agent", "Worker Error", f"Automatic demo worker failed ({type(error).__name__}).")

async def automatic_demo_failure_loop():
    """Inject one demo crash at a time and let the regular monitor/recovery pipeline handle it."""
    global current_system_state
    if not AUTO_DEMO_FAILURES_ENABLED:
        return
    demo_generation = runtime_generation
    await asyncio.sleep(DEMO_FAILURE_START_DELAY_SECONDS)
    if demo_generation != runtime_generation:
        return
    sequence = DEMO_FAILURE_SERVICES[:DEMO_FAILURE_COUNT]

    for target_service in sequence:
        while demo_generation == runtime_generation and (
            current_system_state != "healthy"
            or incident_manager.get_active_incident() is not None
            or any(status != "healthy" for status in simulator.service_states.values())
        ):
            await asyncio.sleep(1)
        if demo_generation != runtime_generation:
            return

        background_agent["demo_failure_current_service"] = target_service
        current_system_state = "anomaly"
        automatic_demo_crashes[target_service] = time.monotonic()
        simulator.trigger_chaos("service_crash", target_service)
        add_log(
            "Background Agent",
            "Critical Demo Failure",
            f"Injected a demo crash for {target_service}; the service is DOWN and the monitoring pipeline will detect it.",
        )

        while demo_generation == runtime_generation and (
            simulator.service_states.get(target_service) != "healthy"
            or incident_manager.get_active_incident() is not None
            or current_system_state != "healthy"
        ):
            await asyncio.sleep(1)
        if demo_generation != runtime_generation:
            return

        background_agent["demo_failures_completed"] += 1
        background_agent["demo_failure_current_service"] = None
        automatic_demo_crashes.pop(target_service, None)
        automatic_demo_incidents.clear()
        add_log("Background Agent", "Demo Recovery", f"Recovery and verification completed for {target_service}.")
        if background_agent["demo_failures_completed"] < len(sequence):
            await asyncio.sleep(DEMO_FAILURE_RECOVERY_PAUSE_SECONDS)

@app.post("/api/auth/register")
async def register_user(credentials: UserRegistration, db=Depends(get_db_session)):
    if not database_ready:
        raise HTTPException(status_code=503, detail="Account storage is unavailable. Configure or restore the backend database.")
    name = credentials.name.strip()
    email = normalize_email(credentials.email)
    password = credentials.password
    if not name or len(name) > 80:
        raise HTTPException(status_code=422, detail="Name must be between 1 and 80 characters.")
    if not valid_email(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password must be between 8 and 128 characters.")
    try:
        if db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status_code=409, detail="An account already exists with this email.")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    user = User(name=name, email=email, password_hash=hash_password(password), role="user")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account already exists with this email.")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    try:
        db.refresh(user)
        token = create_session(db, user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    return {"token": token, "user": public_account(user)}

@app.post("/api/auth/login")
async def login(credentials: AdminLogin, db=Depends(get_db_session)):
    # Admin access is part of the control plane and must remain available while
    # a simulated storefront or auth service outage is being investigated.
    if not database_ready:
        raise HTTPException(status_code=503, detail="Account storage is unavailable. Configure or restore the backend database.")
    if credentials.role not in {None, "user", "admin"}:
        raise HTTPException(status_code=422, detail="Select a valid account role.")
    email = normalize_email(credentials.email)
    try:
        user = db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    if credentials.role in {"user", "admin"} and credentials.role != user.role:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    try:
        token = create_session(db, user)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    return {"token": token, "user": public_account(user), "role": user.role, "name": user.name}

@app.post("/api/auth/logout")
async def logout(
    current_user: User = Depends(require_current_user),
    x_auth_token: str = Header(default=""),
    x_admin_token: str = Header(default=""),
    authorization: str = Header(default=""),
    db=Depends(get_db_session),
):
    del current_user
    try:
        revoke_session(db, x_auth_token or x_admin_token or _bearer_token(authorization))
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Account storage is unavailable.")
    return {"status": "logged_out"}

@app.get("/api/auth/me")
async def get_current_account(current_user: User = Depends(require_current_user)):
    return public_account(current_user)

@app.get("/api/status")
async def get_status():
    """Public health summary; detailed incident data and logs require admin access."""
    incident = incident_manager.get_active_incident()
    return {
        "system_state": current_system_state,
        "uptime_seconds": int(time.monotonic() - backend_started_monotonic),
        "active_incident": ({
            "incident_id": incident["incident_id"],
            "severity": incident["severity"],
            "status": incident["status"],
            "scenario": incident["scenario"]
        } if incident else None)
    }

@app.get("/api/metrics")
async def get_metrics():
    """Returns the current metrics for all simulated boutique services."""
    return simulator.get_metrics()

@app.get("/api/services")
async def get_services():
    return simulator.get_services()

@app.get("/api/services/{service_id}/health")
async def get_service_health(service_id: str):
    service = next((item for item in simulator.get_services() if item["id"] == service_id), None)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    return {"service": service_id, "status": service["status"], "last_health_check": service["last_health_check"], "metrics": {key: service[key] for key in ("cpu_percent", "memory_percent", "requests_per_sec", "error_rate", "latency_p95_ms")}}

@app.get("/api/logs")
async def get_logs(
    limit: int = Query(default=200, ge=1, le=1000),
    service: str | None = None,
    level: str | None = None,
    incident_id: str | None = None,
    search: str | None = None,
    admin: bool = Depends(require_admin)
):
    selected = demo_logs[-limit:]
    if service:
        selected = [log for log in selected if log["service"].lower() == service.lower()]
    if level:
        selected = [log for log in selected if log["level"].lower() == level.lower()]
    if incident_id:
        selected = [log for log in selected if log["incident_id"] == incident_id]
    if search:
        query = search.lower()
        selected = [log for log in selected if query in log["message"].lower() or query in log["agent"].lower()]
    return selected

@app.get("/api/alerts")
async def get_alerts(admin: bool = Depends(require_admin)):
    return alerts

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, admin: bool = Depends(require_admin)):
    alert = next((item for item in alerts if item["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    alert["status"] = "acknowledged"
    alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
    add_log("Admin", "Alert", f"Administrator acknowledged alert {alert_id}.")
    return alert

@app.get("/api/agents")
async def get_agents(admin: bool = Depends(require_admin)):
    names = ["Monitoring Agent", "Detection Agent", "Diagnosis Agent", "Root Cause Agent", "Recommendation Agent", "Recovery Agent", "Verification Agent", "Incident Manager Agent"]
    now = datetime.now(timezone.utc)
    agents = []
    for name in names:
        matching_logs = [log for log in demo_logs if log["agent"] == name or (name == "Diagnosis Agent" and log["agent"] == "Analysis Agent")]
        last_action = matching_logs[-1] if matching_logs else None
        is_active = bool(last_action and (now - datetime.fromisoformat(last_action["time"])).total_seconds() < 10)
        agents.append({
            "name": name,
            "status": "active" if is_active else "standby",
            "current_task": last_action["message"] if is_active else "Waiting for a telemetry event",
            "last_action": last_action["message"] if last_action else "No action recorded yet",
            "timestamp": last_action["time"] if last_action else None,
        })
    return agents

@app.get("/api/agent/status")
async def get_background_agent_status(admin: bool = Depends(require_admin)):
    return {
        **{key: value for key, value in background_agent.items() if key != "activity"},
        "activity": background_agent["activity"][:20],
        "active_incidents": sum(1 for incident in incident_manager.get_all_incidents() if incident["status"] not in {"resolved", "remediation_failed"}),
    }

@app.get("/api/incidents")
async def get_incidents(admin: bool = Depends(require_admin)):
    """Returns all managed incidents."""
    return incident_manager.get_all_incidents()

@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str, admin: bool = Depends(require_admin)):
    """Returns details for a specific incident."""
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    return incident

@app.get("/api/incidents/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str, admin: bool = Depends(require_admin)):
    """Returns timeline events for a specific incident."""
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    return incident.get("timeline", [])

@app.post("/api/reset")
async def reset_demo(admin: bool = Depends(require_admin)):
    """Resets the demo state."""
    global current_system_state, runtime_generation
    runtime_generation += 1
    demo_logs.clear()
    alerts.clear()
    current_system_state = "healthy"
    simulator.reset()
    incident_manager.reset()
    monitor_violation_streaks.clear()
    monitor_clear_streaks.clear()
    monitor_metric_started.clear()
    processed_incidents.clear()
    processing_incidents.clear()
    recovery_in_progress.clear()
    automatic_demo_crashes.clear()
    automatic_demo_incidents.clear()
    background_agent.update({
        "status": "running",
        "auto_recoveries": 0,
        "escalations": 0,
        "last_action": "Demo reset; monitoring resumed",
        "activity": [],
        "demo_failures_completed": 0,
        "demo_failure_current_service": None,
    })
    return {"status": "reset"}

@app.post("/api/trigger_chaos")
async def trigger_chaos(scenario: ChaosScenario, background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    """
    Simulates executing Chaos Mesh which triggers the Multi-Agent pipeline and Incident Manager.
    """
    global current_system_state
    allowed_scenarios = {
        "payment_crash", "payment_high_latency", "frontend_spike", "database_failure",
        "service_crash", "api_error_spike", "cpu_spike", "memory_spike", "network_timeout"
    }
    if scenario.scenario not in allowed_scenarios:
        raise HTTPException(status_code=422, detail=f"Unknown scenario: {scenario.scenario}")
    if scenario.service and scenario.service not in simulator.service_states:
        raise HTTPException(status_code=422, detail="Select a known service.")
    if scenario.scenario == "service_crash" and not scenario.service:
        raise HTTPException(status_code=422, detail="Select a known service to stop.")
    if current_system_state != "healthy":
        raise HTTPException(status_code=409, detail="Resolve or reset the active incident before starting another scenario.")

    current_system_state = "anomaly"

    # Apply scenario to simulator
    simulator.trigger_chaos(scenario.scenario, scenario.service)

    primary_svc = {
        "payment_crash": "paymentservice",
        "payment_high_latency": "paymentservice",
        "frontend_spike": "frontend",
        "database_failure": "database",
        "api_error_spike": scenario.service or "paymentservice",
        "cpu_spike": scenario.service or "frontend",
        "memory_spike": scenario.service or "database",
        "network_timeout": scenario.service or "checkoutservice"
    }.get(scenario.scenario, scenario.service)
    current_metrics = simulator.get_metrics()

    # Create incident in IncidentManager
    incident = incident_manager.create_incident(scenario.scenario, primary_svc, current_metrics)
    incident_id = incident["incident_id"]

    add_alert(primary_svc, incident["severity"], f"{primary_svc} {scenario.scenario.replace('_', ' ')}", "Backend service state changed and telemetry is outside its healthy baseline.", incident_id)

    add_log("System", "Chaos Mesh", f"CRITICAL FAILURE INJECTED: {scenario.scenario} (Incident: {incident_id})")

    return {
        "status": "monitoring",
        "incident_id": incident_id,
        "scenario": scenario.scenario,
        "message": "Background monitor is collecting sustained telemetry before agent analysis."
    }

def classify_recovery_risk(
    scenario: str,
    service: str,
    metrics: dict,
    impact: dict,
    plan: dict | None = None,
    previous_attempts: int = 0,
    critical_sustained: bool = False,
) -> str:
    """Risk is based on the proposed operation, not the incident's severity."""
    del scenario, metrics, impact
    plan = plan or {}
    targets = set(plan.get("targets") or [])
    if plan.get("target"):
        targets.add(plan["target"])
    return policy_classify_recovery_risk(
        action=plan.get("action", "alert_only"),
        target=service if not plan.get("target") else plan.get("target"),
        plan=plan,
        impacted_services=targets or {service},
        previous_attempts=previous_attempts,
        critical_sustained=critical_sustained,
    )


async def orchestrate_agents(scenario: str = "payment_crash", incident_id: str = None, generation: int = None, primary_service: str = None):
    global current_system_state

    try:
        # Wait to simulate metric scraping delay
        await asyncio.sleep(1)
        if generation is not None and generation != runtime_generation:
            return

        # 1. Monitoring Agent
        svc = primary_service or {
            "payment_crash": "paymentservice", "payment_high_latency": "paymentservice",
            "frontend_spike": "frontend", "database_failure": "database"
        }.get(scenario, "frontend")
        all_metrics = simulator.get_metrics()
        current_metrics = all_metrics.get(svc, {"latency_p95_ms": 0, "error_rate": 0})
        latency_duration = time.monotonic() - monitor_metric_started[(svc, "latency")] if (svc, "latency") in monitor_metric_started else 0.0
        error_duration = time.monotonic() - monitor_metric_started[(svc, "errors")] if (svc, "errors") in monitor_metric_started else 0.0
        critical_sustained = critical_metrics_sustained(current_metrics, latency_duration, error_duration)

        # Dynamic Severity & Impact Analysis
        impact = analyze_impact(svc)
        dynamic_severity = evaluate_severity(all_metrics, svc, impact)

        monitoring_result = detect_anomaly({
            "latency": current_metrics["latency_p95_ms"],
            "errors": current_metrics["error_rate"],
            "service": svc,
            "cpu": current_metrics.get("cpu_percent", 0),
            "memory": current_metrics.get("memory_percent", 0),
            "requests_per_sec": current_metrics.get("requests_per_sec", 0),
            "status": simulator.service_states.get(svc, "healthy"),
        })

        add_log("Monitoring Agent", "Alert", monitoring_result["message"])
        current_system_state = "rca"
        add_alert(svc, dynamic_severity, "Anomaly detected", monitoring_result["message"], incident_id)
        add_log("Detection Agent", "Detection", f"Threshold policy matched for {svc}; severity evaluated as {dynamic_severity}. Latency warning starts at {WARNING_LATENCY_MS:g}ms; critical latency is {CRITICAL_LATENCY_MS:g}ms sustained for {CRITICAL_WINDOW_SECONDS:g}s. Recovery approval is based on action risk, not incident severity.")

        if incident_id:
            now_str = datetime.now().strftime("%I:%M:%S %p")
            incident_manager.update_incident(incident_id, {
                "status": "investigating",
                "severity": dynamic_severity,
                "detection_time": now_str,
                "affected_services": impact,
                "symptoms": f"Anomaly detected on {svc}. Latency: {current_metrics['latency_p95_ms']}ms, Error Rate: {current_metrics['error_rate']}%"
            })
            incident_manager.add_timeline_event(
                incident_id,
                stage="Detection",
                title="Anomaly Detected",
                description=monitoring_result["message"],
                agent="Monitoring Agent"
            )

        await asyncio.sleep(1)
        if generation is not None and generation != runtime_generation:
            return

        # 2. Analysis Agent
        observed_logs = [log["message"] for log in demo_logs[-80:] if svc in log["message"].lower() or log["agent"].lower() == svc]
        pseudo_logs = "\n".join(observed_logs) or f"ERROR: {svc} failure detected. Scenario={scenario}."
        analysis_result = analyze_logs(pseudo_logs)
        add_log("Analysis", "Log parsing", analysis_result["summary"])
        add_log("Diagnosis Agent", "Diagnosis", f"Correlated observed service logs with the {scenario} telemetry signature.")

        if incident_id:
            incident_manager.add_timeline_event(
                incident_id,
                stage="Log Analysis",
                title="Log Parsing Completed",
                description=analysis_result["summary"],
                agent="Analysis Agent"
            )

        await asyncio.sleep(1)
        if generation is not None and generation != runtime_generation:
            return

        # 3. RCA Agent
        rca_result = root_cause(analysis_result["summary"], svc)
        add_log("Root Cause Agent", "Root Cause", rca_result["root_cause"])
        current_system_state = "remediation"

        if incident_id:
            incident_manager.update_incident(incident_id, {
                "status": "rca",
                "root_cause": rca_result["root_cause"],
                "evidence": f"Log dump indicates critical failure in {svc} container."
            })
            incident_manager.add_timeline_event(
                incident_id,
                stage="Root Cause Analysis",
                title="Root Cause Identified",
                description=rca_result["root_cause"],
                agent="RCA Agent"
            )

        await asyncio.sleep(1)
        if generation is not None and generation != runtime_generation:
            return

        # 4. Remediation Agent
        remediation_plan = determine_remediation(rca_result)
        add_log("Recommendation Agent", "Action", remediation_plan["message"])

        if scenario == "payment_high_latency" and remediation_plan.get("action") == "scale_deployment" and not critical_sustained:
            # A brief warning is an investigation signal, not a scale command.
            # Observe through the configured critical window before deciding.
            observation_deadline = time.monotonic() + CRITICAL_WINDOW_SECONDS + 1
            healthy_samples = 0
            latest_metrics = all_metrics
            while time.monotonic() < observation_deadline:
                await asyncio.sleep(1)
                if generation is not None and generation != runtime_generation:
                    return
                latest_metrics = simulator.get_metrics()
                current_metrics = latest_metrics.get(svc, {"latency_p95_ms": 0, "error_rate": 0})
                latency_duration = time.monotonic() - monitor_metric_started[(svc, "latency")] if (svc, "latency") in monitor_metric_started else 0.0
                error_duration = time.monotonic() - monitor_metric_started[(svc, "errors")] if (svc, "errors") in monitor_metric_started else 0.0
                critical_sustained = critical_metrics_sustained(current_metrics, latency_duration, error_duration)
                if critical_sustained or simulator.service_states.get(svc) == "down":
                    break
                transiently_healthy = (
                    simulator.service_states.get(svc) == "healthy"
                    and current_metrics.get("latency_p95_ms", float("inf")) < WARNING_LATENCY_MS
                    and current_metrics.get("error_rate", float("inf")) < CRITICAL_ERROR_RATE_PERCENT
                )
                healthy_samples = healthy_samples + 1 if transiently_healthy else 0
                if healthy_samples >= 3:
                    if incident_id:
                        incident_manager.add_timeline_event(incident_id, "Monitoring", "Transient spike cleared", "Latency returned below the warning threshold for three consecutive samples; no scaling or approval request was needed.", "Monitoring Agent")
                        incident_manager.resolve_incident(incident_id, "The temporary latency spike cleared during observation; no recovery action was applied.")
                    current_system_state = "healthy"
                    background_agent["last_action"] = f"Transient latency on {svc} cleared; continued monitoring without scaling."
                    add_log("Monitoring Agent", "Resolution", f"Transient latency on {svc} cleared during observation; no scaling or approval was needed.")
                    return
            if not critical_sustained and simulator.service_states.get(svc) != "down":
                if incident_id:
                    incident_manager.update_incident(incident_id, {
                        "status": "monitoring",
                        "risk_level": "medium",
                        "approval_status": "not_required",
                        "recovery_action": None,
                        "recovery_status": "monitoring",
                        "recommended_remediation": "Continue monitoring; the critical latency/error threshold was not sustained, so no scaling action was taken.",
                    })
                    incident_manager.add_timeline_event(incident_id, "Monitoring", "Critical window not met", "Latency did not remain above the configured critical threshold for the observation window. No approval was requested and no scaling action was applied.", "Monitoring Agent")
                current_system_state = "anomaly"
                background_agent["last_action"] = f"Monitoring {svc}; the critical window was not met, so no scaling action was taken."
                add_log("Monitoring Agent", "Observation", f"Critical window not met for {svc}; continued monitoring without scaling or an approval request.")
                return
            all_metrics = latest_metrics
            current_metrics = all_metrics.get(svc, current_metrics)

        latency_duration = time.monotonic() - monitor_metric_started[(svc, "latency")] if (svc, "latency") in monitor_metric_started else 0.0
        error_duration = time.monotonic() - monitor_metric_started[(svc, "errors")] if (svc, "errors") in monitor_metric_started else 0.0
        critical_sustained = critical_sustained or critical_metrics_sustained(current_metrics, latency_duration, error_duration)
        dynamic_severity = evaluate_severity(all_metrics, svc, impact)
        risk_level = classify_recovery_risk(
            scenario, svc, all_metrics, impact, remediation_plan,
            critical_sustained=critical_sustained,
        )
        demo_crash_started = automatic_demo_incidents.get(incident_id)
        if demo_crash_started is not None:
            remaining_down_time = DEMO_FAILURE_MIN_DOWN_SECONDS - (time.monotonic() - demo_crash_started)
            if remaining_down_time > 0:
                await asyncio.sleep(remaining_down_time)
                if generation is not None and generation != runtime_generation:
                    return

        if incident_id:
            incident_manager.update_incident(incident_id, {
                "status": "awaiting_approval" if risk_level in {"high", "critical"} else "recovering",
                "approval_status": "pending" if risk_level in {"high", "critical"} else "not_required",
                "severity": dynamic_severity,
                "symptoms": f"Observed {svc} telemetry after the decision window. Latency: {current_metrics.get('latency_p95_ms', 0)}ms, Error Rate: {current_metrics.get('error_rate', 0)}%",
                "risk_level": risk_level,
                "recommended_remediation": remediation_plan.get("message", "Apply the recommended recovery action"),
                "recovery_action": remediation_plan
            })
            incident_manager.add_timeline_event(
                incident_id,
                stage="Remediation Strategy",
                title=f"{risk_level.title()}-risk remediation selected",
                description=f"{remediation_plan.get('message', 'Selected remediation strategy')} Risk policy: {risk_level}; {'administrator approval required' if risk_level in {'high', 'critical'} else 'bounded automatic recovery allowed'}. {'Critical telemetry remained above the configured threshold for the observation window.' if critical_sustained else 'No sustained critical latency or error window was observed at decision time.'}",
                agent="Remediation Agent"
            )

        if risk_level in {"high", "critical"}:
            current_system_state = "awaiting_approval"
            background_agent["escalations"] += 1
            background_agent["last_action"] = f"Escalated {incident_id} ({risk_level} risk) for approval"
            add_log("Incident Manager Agent", "Approval", f"{risk_level.title()}-risk recovery for {incident_id} requires administrator approval.")
            add_alert(svc, dynamic_severity, "Recovery awaiting approval", remediation_plan.get("message", "Review the recovery recommendation."), incident_id)
        else:
            current_system_state = "recovering"
            background_agent["last_action"] = f"Auto-recovering {svc}: {remediation_plan.get('action', 'safe recovery')}"
            add_log("Incident Manager Agent", "Recovery", f"{risk_level.title()}-risk incident {incident_id} is within the automatic recovery policy; applying a bounded action.")
            asyncio.create_task(execute_approved_recovery(incident_id, generation if generation is not None else runtime_generation, automatic=True))

    except Exception as e:
        add_log("System", "Error", f"Orchestration pipeline exception: {str(e)}")
        if incident_id:
            incident_manager.fail_incident(incident_id, f"Pipeline exception: {str(e)}")
        current_system_state = "degraded"
    finally:
        if incident_id:
            processing_incidents.discard(incident_id)

async def execute_approved_recovery(incident_id: str, generation: int, automatic: bool = False):
    global current_system_state
    if incident_id in recovery_in_progress:
        return
    recovery_in_progress.add(incident_id)
    try:
        await _execute_recovery_once(incident_id, generation, automatic)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        incident = incident_manager.get_incident_by_id(incident_id)
        add_log("Recovery Agent", "Error", f"Recovery runner failed ({type(error).__name__}); no success was recorded.")
        if incident and automatic:
            incident_manager.update_incident(incident_id, {
                "status": "awaiting_approval",
                "approval_status": "pending",
                "risk_level": "high",
                "recovery_status": "escalated",
                "recommended_remediation": "Automatic recovery encountered an internal error. Review the incident and choose the next action.",
            })
            incident_manager.add_timeline_event(incident_id, "Escalation", "Recovery runner stopped", f"The automatic recovery worker stopped after {type(error).__name__}; no healthy state was assumed.", "Incident Manager Agent")
            background_agent["escalations"] += 1
            current_system_state = "awaiting_approval"
            add_alert((incident.get("affected_services", {}).get("directly_affected") or ["AutoSRE"])[0], incident.get("severity", "P2"), "Recovery worker error", "Automatic recovery stopped unexpectedly; administrator review is required.", incident_id)
        elif incident:
            incident_manager.fail_incident(incident_id, "The approved recovery worker stopped unexpectedly.")
            current_system_state = "degraded"
    finally:
        recovery_in_progress.discard(incident_id)


async def _execute_recovery_once(incident_id: str, generation: int, automatic: bool = False):
    global current_system_state
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident or generation != runtime_generation:
        return
    plan = incident.get("recovery_action") or {"action": "restart_simulation", "target": "all"}
    target = plan.get("target") or (incident.get("affected_services", {}).get("directly_affected") or ["frontend"])[0]
    max_attempts = AUTOMATIC_RECOVERY_ATTEMPTS if automatic else 1
    attempts_before_action = int(incident.get("recovery_attempts", 0))
    for attempt in range(1, max_attempts + 1):
        if generation != runtime_generation:
            return
        attempt_number = attempts_before_action + attempt
        incident_manager.update_incident(incident_id, {"recovery_attempts": attempt_number, "recovery_status": "executing"})
        label = "automatic" if automatic else "approved"
        attempt_label = f"Attempt {attempt}/{max_attempts}" if automatic else "Approved action"
        add_log("Recovery Agent", "Recovery", f"{attempt_label}: executing {label} action: {plan.get('message', plan.get('action'))}")
        result = execute_deployment(plan)
        if result.get("status") == "success":
            action = plan.get("action")
            if action == "scale_deployment" and not simulator.scale_service(target, int(plan.get("replicas", 3))):
                result = {"status": "failed", "message": f"Scaling policy rejected the requested replica count; safe limit is {SAFE_REPLICA_LIMIT}."}
            elif action in {"restart_service", "restart_pod", "restore_connection", "reduce_load", "retry_request", "remove_bad_replica", "scale_deployment"}:
                simulator.begin_recovery(target)
                await asyncio.sleep(1.5)
                if generation != runtime_generation:
                    return
                if not simulator.recover_service(target):
                    result = {"status": "failed", "message": f"Recovery target {target} did not match the active simulated failure."}
            else:
                result = {"status": "failed", "message": result.get("message", "No safe recovery action was available.")}

        if result.get("status") == "success":
            incident_manager.update_incident(incident_id, {"executed_action": result.get("message"), "recovery_status": "verifying"})
            incident_manager.add_timeline_event(incident_id, "Recovery Execution", f"{label.title()} recovery executed", result.get("message", "Recovery action applied."), "Recovery Agent")
            add_log("Recovery Agent", "Action", result.get("message", "Recovery action applied."))
            current_system_state = "recovering"
            affected = set(simulator.last_recovery_affected or [target])
            incident_impact = incident.get("affected_services", {})
            required_services = sorted(affected | set(incident_impact.get("directly_affected", [])))
            healthy_samples = 0
            for _ in range(3):
                await asyncio.sleep(1)
                if generation != runtime_generation:
                    return
                metrics = simulator.get_metrics()
                metrics_ok = all(
                    metrics.get(name, {}).get("error_rate", 100) < CRITICAL_ERROR_RATE_PERCENT
                    and metrics.get(name, {}).get("latency_p95_ms", float("inf")) < CRITICAL_LATENCY_MS
                    and metrics.get(name, {}).get("cpu_percent", 100) < 95
                    and metrics.get(name, {}).get("memory_percent", 100) < 97
                    for name in required_services
                )
                if metrics_ok:
                    healthy_samples += 1
                else:
                    healthy_samples = 0

            if healthy_samples == 3 and simulator.complete_recovery(required_services):
                incident_manager.add_timeline_event(incident_id, "Verification", "Post-recovery health check passed", f"Targeted service health and critical telemetry stayed within configured recovery thresholds for three consecutive samples. Critical latency is {CRITICAL_LATENCY_MS:g}ms; critical error rate is {CRITICAL_ERROR_RATE_PERCENT:g}%.", "Verification Agent")
                add_log("Verification Agent", "Health Check", "Recovery verified: services are healthy and telemetry is within baseline limits.")
                incident_manager.update_incident(incident_id, {"auto_recovered": automatic, "approval_status": "not_required" if automatic else "approved"})
                incident_manager.resolve_incident(incident_id, f"{label.title()} recovery completed and post-recovery checks passed.")
                for alert in alerts:
                    if alert.get("incident_id") == incident_id:
                        alert["status"] = "resolved"
                if automatic:
                    background_agent["auto_recoveries"] += 1
                background_agent["last_action"] = f"Recovered {target}; verification passed"
                current_system_state = "healthy" if all(status == "healthy" for status in simulator.service_states.values()) else "anomaly"
                return
            simulator.fail_recovery(required_services)
            result = {"status": "failed", "message": "Targeted post-recovery health checks did not pass for three consecutive samples."}

        incident_manager.add_timeline_event(incident_id, "Verification", f"Recovery attempt {attempt_number} failed", result.get("message", "Recovery action failed."), "Verification Agent")
        add_log("Verification Agent", "Error", f"Recovery attempt {attempt_number} failed: {result.get('message', 'Unknown recovery error')}")
        if automatic and attempt < max_attempts:
            await asyncio.sleep(0.5)

    if automatic:
        incident_manager.update_incident(incident_id, {
            "status": "awaiting_approval",
            "approval_status": "pending",
            "risk_level": "high",
            "recovery_status": "escalated",
            "recommended_remediation": f"{max_attempts} bounded automatic recovery attempts failed. Review and approve: {plan.get('message', plan.get('action'))}",
        })
        incident_manager.add_timeline_event(incident_id, "Escalation", "Automatic recovery limit reached", f"{max_attempts} bounded automatic recovery attempts failed; an administrator must review the next action.", "Incident Manager Agent")
        background_agent["escalations"] += 1
        background_agent["last_action"] = f"Escalated {incident_id} after {max_attempts} failed automatic attempts"
        current_system_state = "awaiting_approval"
        add_log("Incident Manager Agent", "Approval", f"Incident {incident_id} escalated after {max_attempts} failed automatic recovery attempts; administrator approval is required.")
        add_alert(target, incident.get("severity", "P2"), "Automatic recovery escalated", incident["recommended_remediation"], incident_id)
    else:
        incident_manager.fail_incident(incident_id, result.get("message", "Recovery failed."))
        current_system_state = "degraded"

@app.post("/api/incidents/{incident_id}/approve-recovery")
async def approve_recovery(incident_id: str, background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    global current_system_state
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.get("status") != "awaiting_approval" or incident.get("approval_status") != "pending":
        raise HTTPException(status_code=409, detail="This incident has no pending recovery approval.")
    incident_manager.update_incident(incident_id, {"approval_status": "approved", "status": "recovering"})
    incident_manager.add_timeline_event(incident_id, "Admin Approval", "Recovery approved", "An authenticated administrator approved the recommended recovery.", "Admin")
    current_system_state = "recovering"
    background_tasks.add_task(execute_approved_recovery, incident_id, runtime_generation)
    return {"status": "recovery_started", "incident_id": incident_id}

@app.post("/api/incidents/{incident_id}/reject-recovery")
async def reject_recovery(incident_id: str, admin: bool = Depends(require_admin)):
    global current_system_state
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if incident.get("status") != "awaiting_approval" or incident.get("approval_status") != "pending":
        raise HTTPException(status_code=409, detail="This incident has no pending recovery approval.")
    incident_manager.update_incident(incident_id, {"approval_status": "rejected", "status": "awaiting_manual_action"})
    incident_manager.add_timeline_event(incident_id, "Admin Decision", "Recovery rejected", "An administrator rejected the recommendation; the system remains degraded for manual action.", "Admin")
    add_log("Admin", "Approval", f"Recovery rejected for {incident_id}; service remains degraded.")
    current_system_state = "degraded"
    return {"status": "rejected", "incident_id": incident_id}

@app.post("/api/chaos/high-latency")
async def chaos_high_latency(background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    return await trigger_chaos(ChaosScenario(scenario="payment_high_latency"), background_tasks, admin)

@app.post("/api/chaos/traffic-spike")
async def chaos_traffic_spike(background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    return await trigger_chaos(ChaosScenario(scenario="frontend_spike"), background_tasks, admin)

@app.post("/api/chaos/database-failure")
async def chaos_database_failure(background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    return await trigger_chaos(ChaosScenario(scenario="database_failure"), background_tasks, admin)

@app.post("/api/chaos/{service}/stop")
async def stop_service(service: str, background_tasks: BackgroundTasks, admin: bool = Depends(require_admin)):
    if service not in simulator.service_states:
        raise HTTPException(status_code=404, detail="Unknown service.")
    return await trigger_chaos(ChaosScenario(scenario="service_crash", service=service), background_tasks, admin)

@app.post("/api/chaos/{service}/start")
async def start_service(service: str, admin: bool = Depends(require_admin)):
    global current_system_state
    if service not in simulator.service_states:
        raise HTTPException(status_code=404, detail="Unknown service.")
    if simulator.service_states[service] == "healthy":
        return {"status": "already_healthy", "service": service}
    if not simulator.recover_service(service):
        raise HTTPException(status_code=409, detail="The active simulated failure targets a different service. Resolve that incident first.")
    affected = simulator.last_recovery_affected[:]
    healthy_samples = 0
    for _ in range(3):
        await asyncio.sleep(1)
        metrics = simulator.get_metrics()
        metrics_ok = all(
            metrics.get(name, {}).get("error_rate", 100) < CRITICAL_ERROR_RATE_PERCENT
            and metrics.get(name, {}).get("latency_p95_ms", float("inf")) < CRITICAL_LATENCY_MS
            and metrics.get(name, {}).get("cpu_percent", 100) < 95
            and metrics.get(name, {}).get("memory_percent", 100) < 97
            for name in affected
        )
        healthy_samples = healthy_samples + 1 if metrics_ok else 0
    if healthy_samples < 3 or not simulator.complete_recovery(affected):
        simulator.fail_recovery(affected)
        raise HTTPException(status_code=503, detail="The service restart was applied, but its health verification failed.")
    incident = incident_manager.get_active_incident()
    if incident:
        incident_manager.update_incident(incident["incident_id"], {"approval_status": "manual_recovery", "auto_recovered": False, "executed_action": f"Administrator restarted {service}."})
        incident_manager.add_timeline_event(incident["incident_id"], "Admin Recovery", "Service restarted", f"Administrator restarted {service}.", "Admin")
        incident_manager.add_timeline_event(incident["incident_id"], "Verification", "Health check passed", f"Targeted service metrics passed three consecutive samples for {', '.join(affected)}.", "Verification Agent")
        incident_manager.resolve_incident(incident["incident_id"], "Administrator restarted the service and health checks passed.")
    add_log("Admin", "Recovery", f"Administrator started {service}.")
    current_system_state = "healthy" if all(status == "healthy" for status in simulator.service_states.values()) else "anomaly"
    return {"status": "healthy", "service": service}

def order_to_dict(order: Order) -> dict:
    order_time = order.timestamp
    if order_time.tzinfo is None:
        order_time = order_time.replace(tzinfo=timezone.utc)
    return {
        "order_id": order.order_id,
        "user_id": order.user_id,
        "items": order.items,
        "totalAmount": order.total_amount,
        "paymentMethod": order.payment_method,
        "paymentStatus": order.payment_status,
        "status": order.status,
        "address": order.address,
        "timestamp": order_time.isoformat(),
        "deliveryOption": order.delivery_option,
        "deliveryEstimate": order.delivery_estimate,
    }

@app.get("/api/orders")
async def get_orders(current_user: User = Depends(require_current_user), db=Depends(get_db_session)):
    if simulator.service_states.get("frontend") != "healthy":
        raise HTTPException(status_code=503, detail="Frontend service is temporarily unavailable.")
    if simulator.service_states.get("checkoutservice") != "healthy":
        raise HTTPException(status_code=503, detail="Order service is temporarily unavailable.")
    return [order_to_dict(order) for order in db.scalars(
        select(Order).where(Order.user_id == current_user.id).order_by(Order.timestamp.desc()).limit(100)
    )]

async def progress_order(order_id: str):
    stages = ["CONFIRMED", "PACKED", "SHIPPED", "OUT FOR DELIVERY", "DELIVERED"]
    if not database_ready or SessionLocal is None:
        return
    with SessionLocal() as db:
        saved_order = db.get(Order, order_id)
        if not saved_order or saved_order.payment_status != "cash_on_delivery":
            return
        if saved_order.status in stages:
            stages = stages[stages.index(saved_order.status) + 1:]
    for stage in stages:
        await asyncio.sleep(3)
        if simulator.service_states.get("checkoutservice") != "healthy":
            return
        if not database_ready or SessionLocal is None:
            return
        try:
            with SessionLocal() as db:
                order = db.get(Order, order_id)
                if not order or order.status in {"DELIVERED", "CANCELLED"}:
                    return
                order.status = stage
                db.commit()
            add_log("Order Service", "Order Update", f"Order {order_id} status changed to {stage}.")
        except SQLAlchemyError as error:
            add_log("Order Service", "Error", f"Order status update could not be saved ({type(error).__name__}).")
            return

@app.post("/api/orders")
async def place_order(
    order: OrderRequest,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    current_user: User = Depends(require_current_user),
    db=Depends(get_db_session),
):
    unavailable_services = (
        ("frontend", "Frontend service"),
        ("cartservice", "Cart service"),
        ("checkoutservice", "Order service"),
        ("paymentservice", "Payment service"),
    )
    for service_id, label in unavailable_services:
        if simulator.service_states.get(service_id) != "healthy":
            raise HTTPException(status_code=503, detail=f"{label} is temporarily unavailable.")
    if not order.items:
        raise HTTPException(status_code=422, detail="Your cart is empty.")
    if not 8 <= len(idempotency_key) <= 128:
        raise HTTPException(status_code=422, detail="A valid Idempotency-Key header is required to prevent duplicate orders.")
    if len(order.items) > 50:
        raise HTTPException(status_code=422, detail="An order can contain at most 50 line items.")
    if order.deliveryOption not in {"standard", "express"}:
        raise HTTPException(status_code=422, detail="Select a valid delivery option.")
    payment_method = order.paymentMethod.strip().upper()
    if payment_method not in {"UPI", "CARD", "NETBANKING", "COD"}:
        raise HTTPException(status_code=422, detail="Select a valid payment method.")
    normalized_items = []
    subtotal = 0.0
    for item in order.items:
        try:
            item_id = str(item["id"])
            item_name = str(item["name"]).strip()
            price = float(item["price"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=422, detail="Each order item needs an id, name, price, and quantity.")
        if not item_id or not item_name or len(item_name) > 160 or not (0 < price <= 10_000_000) or not (1 <= quantity <= 100):
            raise HTTPException(status_code=422, detail="One or more order items contain invalid values.")
        normalized_items.append({"id": item_id[:80], "name": item_name, "price": round(price, 2), "quantity": quantity})
        subtotal += price * quantity
    if not order.address.strip() or len(order.address) > 500:
        raise HTTPException(status_code=422, detail="Enter a valid delivery address.")
    expected_total = subtotal + (99 if order.deliveryOption == "express" else 0 if subtotal > 999 else 49)
    if abs(expected_total - order.totalAmount) > 0.02:
        raise HTTPException(status_code=422, detail="The order total does not match its items and delivery option.")
    if not (0 < order.totalAmount <= 100_000_000):
        raise HTTPException(status_code=422, detail="Enter a valid order total.")

    request_body = {
        "items": normalized_items,
        "totalAmount": round(order.totalAmount, 2),
        "paymentMethod": payment_method,
        "address": order.address.strip(),
        "deliveryOption": order.deliveryOption,
    }
    request_hash = hashlib.sha256(json.dumps(request_body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    previous_order = db.scalar(select(Order).where(
        Order.user_id == current_user.id,
        Order.idempotency_key == idempotency_key,
    ))
    if previous_order:
        if previous_order.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="This order retry key was already used with different checkout details.")
        return {"order": order_to_dict(previous_order), "replayed": True}

    now = datetime.now(timezone.utc)
    record = Order(
        order_id=f"AS-{now.strftime('%y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
        user_id=current_user.id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        items=normalized_items,
        total_amount=round(order.totalAmount, 2),
        payment_method=payment_method,
        # There is no payment gateway in this demo: never claim a real payment succeeded.
        payment_status="cash_on_delivery" if payment_method == "COD" else "payment_pending_demo",
        status="PLACED",
        address=order.address.strip(),
        delivery_option=order.deliveryOption,
        delivery_estimate="Today by 9 PM" if order.deliveryOption == "express" else "Delivery by Tomorrow",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous_order = db.scalar(select(Order).where(
            Order.user_id == current_user.id,
            Order.idempotency_key == idempotency_key,
        ))
        if previous_order and previous_order.request_hash == request_hash:
            return {"order": order_to_dict(previous_order), "replayed": True}
        raise HTTPException(status_code=409, detail="The order could not be saved because this retry key conflicts with another request.")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Order storage is unavailable. Please retry with the same checkout session.")
    record = db.get(Order, record.order_id)
    result = order_to_dict(record)
    add_log("Order Service", "Order", f"Order {record.order_id} was recorded with payment status {record.payment_status}.")
    if record.payment_status == "cash_on_delivery":
        task = asyncio.create_task(progress_order(record.order_id))
        order_progress_tasks.add(task)
        task.add_done_callback(order_progress_tasks.discard)
    return {"order": result, "replayed": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
