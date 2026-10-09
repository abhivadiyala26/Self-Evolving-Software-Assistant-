import asyncio
import random
import time
from datetime import datetime, timezone
from services.recovery_policy import SAFE_REPLICA_LIMIT

SERVICES = [
    "frontend", "authservice", "cartservice", "checkoutservice", "recommendationservice",
    "productcatalogservice", "paymentservice", "shippingservice",
    "emailservice", "currencyservice", "adservice", "loadgenerator", "database"
]

DEPENDENCIES = {
    "frontend": ["authservice", "cartservice", "checkoutservice", "productcatalogservice"],
    "cartservice": ["checkoutservice", "database"],
    "checkoutservice": ["paymentservice", "shippingservice", "database"],
    "paymentservice": ["database"],
    "productcatalogservice": ["database"],
    "recommendationservice": ["productcatalogservice"],
    "shippingservice": ["database"],
    "emailservice": ["checkoutservice"],
    "currencyservice": [], "adservice": [], "loadgenerator": [], "database": []
}

class BoutiqueSimulator:
    def __init__(self):
        self.metrics = {
            svc: {"requests_per_sec": 0, "error_rate": 0.0, "latency_p95_ms": 0, "cpu_percent": 0, "memory_percent": 0}
            for svc in SERVICES
        }
        self.chaos_scenario = None
        self.scenario_started_at = None
        self.service_states = {svc: "healthy" for svc in SERVICES}
        self.replicas = {svc: 2 for svc in SERVICES}
        self.is_running = False
        self.last_recovery_affected = []

    def trigger_chaos(self, scenario, target_service=None):
        self.chaos_scenario = scenario
        self.target_service = target_service or {
            "payment_crash": "paymentservice",
            "payment_high_latency": "paymentservice",
            "frontend_spike": "frontend",
            "database_failure": "database",
            "api_error_spike": "paymentservice",
            "cpu_spike": "frontend",
            "memory_spike": "database",
            "network_timeout": "checkoutservice",
        }.get(scenario)
        self.scenario_started_at = time.time()
        if scenario == "service_crash" and target_service in self.service_states:
            self.service_states[target_service] = "down"
        if scenario == "payment_crash":
            self.service_states["paymentservice"] = "down"
        elif scenario == "payment_high_latency":
            self.service_states["paymentservice"] = "degraded"
        elif scenario == "frontend_spike":
            self.service_states["frontend"] = "degraded"
        elif scenario == "database_failure":
            self.service_states["database"] = "down"
            self.service_states["checkoutservice"] = "degraded"
            self.service_states["paymentservice"] = "degraded"
        elif scenario in {"api_error_spike", "cpu_spike", "memory_spike", "network_timeout"}:
            if self.target_service in self.service_states:
                self.service_states[self.target_service] = "degraded"

    def reset(self):
        self.chaos_scenario = None
        self.target_service = None
        self.scenario_started_at = None
        self.service_states = {svc: "healthy" for svc in SERVICES}
        self.replicas = {svc: 2 for svc in SERVICES}
        self.last_recovery_affected = []
        self.generate_baseline_metrics()

    def begin_recovery(self, service):
        """Expose the in-progress recovery state before verification restores health."""
        if service not in self.service_states:
            return False
        self.service_states[service] = "recovering"
        return True

    def recover_service(self, service):
        """Prepare a targeted recovery; verification must call complete_recovery."""
        if service not in self.service_states:
            return False
        if self.chaos_scenario and self.target_service != service:
            return False

        affected = {service}
        if self.target_service == service:
            affected.update({
                "payment_crash": {"paymentservice", "checkoutservice", "frontend"},
                "payment_high_latency": {"paymentservice", "checkoutservice", "frontend"},
                "frontend_spike": {"frontend", "cartservice"},
                "database_failure": {"database", "checkoutservice", "paymentservice"},
            }.get(self.chaos_scenario, {service}))
            self.chaos_scenario = None
            self.target_service = None
            self.scenario_started_at = None

        self.last_recovery_affected = [name for name in affected if name in self.service_states]
        for name in self.last_recovery_affected:
            self.service_states[name] = "recovering"
            self._generate_service_metrics(name)
        return True

    def complete_recovery(self, services=None):
        """Mark only verified recovery targets healthy."""
        targets = services if services is not None else self.last_recovery_affected
        for service in targets:
            if service in self.service_states and self.service_states[service] == "recovering":
                self.service_states[service] = "healthy"
        return all(self.service_states.get(service) == "healthy" for service in targets)

    def fail_recovery(self, services=None):
        targets = services if services is not None else self.last_recovery_affected
        for service in targets:
            if service in self.service_states and self.service_states[service] == "recovering":
                self.service_states[service] = "degraded"

    def _generate_service_metrics(self, service):
        base_rps = 100 if service in ["frontend", "loadgenerator"] else random.randint(20, 80)
        self.metrics[service]["requests_per_sec"] = base_rps + random.randint(-10, 10)
        self.metrics[service]["error_rate"] = round(random.uniform(0.0, 0.5), 2)
        self.metrics[service]["latency_p95_ms"] = random.randint(10, 60)
        self.metrics[service]["cpu_percent"] = round(random.uniform(18, 62), 1)
        self.metrics[service]["memory_percent"] = round(random.uniform(35, 76), 1)

    def scale_service(self, service, replicas):
        if service not in self.replicas or replicas < 1 or replicas > SAFE_REPLICA_LIMIT:
            return False
        self.replicas[service] = replicas
        return True

    def get_services(self):
        checked_at = datetime.now(timezone.utc).isoformat()
        return [
            {
                "id": svc,
                "name": svc,
                "status": self.service_states[svc],
                "dependencies": DEPENDENCIES.get(svc, []),
                "cpu_percent": self.metrics[svc]["cpu_percent"],
                "memory_percent": self.metrics[svc]["memory_percent"],
                "requests_per_sec": self.metrics[svc]["requests_per_sec"],
                "error_rate": self.metrics[svc]["error_rate"],
                "latency_p95_ms": self.metrics[svc]["latency_p95_ms"],
                "uptime_percent": 99.99 if self.service_states[svc] == "healthy" else 97.5 if self.service_states[svc] == "degraded" else 92.0,
                "replicas": 0 if self.service_states[svc] == "down" else self.replicas[svc],
                "last_health_check": checked_at,
            }
            for svc in SERVICES
        ]

    def get_metrics(self):
        database_latency = self.metrics.get("database", {}).get("latency_p95_ms", 0)
        for values in self.metrics.values():
            rps = values["requests_per_sec"]
            values["active_connections"] = int(rps * 0.72)
            values["throughput_mbps"] = round(rps * 0.008, 2)
            values["http_4xx_per_sec"] = round(rps * 0.006, 2)
            values["http_5xx_per_sec"] = round(rps * values["error_rate"] / 100, 2)
            values["database_latency_ms"] = database_latency
        return self.metrics

    def generate_baseline_metrics(self):
        for svc in SERVICES:
            self._generate_service_metrics(svc)

    def apply_chaos_metrics(self):
        if not self.chaos_scenario:
            return
            
        if self.chaos_scenario == "payment_crash":
            self.metrics["paymentservice"]["error_rate"] = round(random.uniform(80.0, 100.0), 2)
            self.metrics["paymentservice"]["latency_p95_ms"] = random.randint(2000, 5000)
            self.metrics["paymentservice"]["cpu_percent"] = round(random.uniform(75, 96), 1)
            self.metrics["paymentservice"]["memory_percent"] = round(random.uniform(72, 91), 1)
            self.metrics["checkoutservice"]["error_rate"] = round(random.uniform(40.0, 60.0), 2)
            self.metrics["checkoutservice"]["latency_p95_ms"] = random.randint(1000, 2000)
            self.metrics["frontend"]["error_rate"] = round(random.uniform(10.0, 20.0), 2)
            self.metrics["frontend"]["latency_p95_ms"] = random.randint(500, 1500)
            
        elif self.chaos_scenario == "payment_high_latency":
            progression = [50, 200, 500, 1000, 1250]
            elapsed = int(max(0, time.time() - (self.scenario_started_at or time.time())))
            latency = progression[min(elapsed, len(progression) - 1)]
            self.metrics["paymentservice"]["latency_p95_ms"] = latency
            error_progression = [0.4, 2.0, 7.5, 13.0, 18.0]
            phase = min(elapsed, len(error_progression) - 1)
            self.metrics["paymentservice"]["error_rate"] = error_progression[phase]
            self.metrics["paymentservice"]["requests_per_sec"] = 145 + min(85, elapsed * 18)
            self.metrics["paymentservice"]["cpu_percent"] = round(min(91, 32 + elapsed * 15), 1)
        elif self.chaos_scenario == "database_failure":
            self.metrics["database"].update(error_rate=100.0, latency_p95_ms=2500)
            self.metrics["database"].update(cpu_percent=88.0, memory_percent=92.0)
            for svc in ("checkoutservice", "paymentservice"):
                self.metrics[svc]["error_rate"] = round(random.uniform(35, 55), 2)
                self.metrics[svc]["latency_p95_ms"] = random.randint(700, 1400)
        elif self.chaos_scenario == "service_crash" and self.target_service in self.metrics:
            self.metrics[self.target_service].update(error_rate=100.0, latency_p95_ms=2500)
        elif self.chaos_scenario == "frontend_spike":
            self.metrics["frontend"]["requests_per_sec"] = random.randint(2000, 3000)
            self.metrics["frontend"]["latency_p95_ms"] = random.randint(500, 1500)
            self.metrics["frontend"]["error_rate"] = round(random.uniform(20.0, 40.0), 2)
            self.metrics["frontend"]["cpu_percent"] = round(random.uniform(80.0, 96.0), 1)
            self.metrics["frontend"]["memory_percent"] = round(random.uniform(70.0, 90.0), 1)
            self.metrics["cartservice"]["latency_p95_ms"] = random.randint(300, 800)
        elif self.chaos_scenario == "api_error_spike" and self.target_service in self.metrics:
            target = self.metrics[self.target_service]
            target.update(error_rate=35.0, latency_p95_ms=650)
            target["requests_per_sec"] = max(target["requests_per_sec"], 120)
        elif self.chaos_scenario == "cpu_spike" and self.target_service in self.metrics:
            self.metrics[self.target_service].update(cpu_percent=94.0, latency_p95_ms=420, error_rate=8.0)
        elif self.chaos_scenario == "memory_spike" and self.target_service in self.metrics:
            self.metrics[self.target_service].update(memory_percent=96.0, latency_p95_ms=380, error_rate=5.5)
        elif self.chaos_scenario == "network_timeout" and self.target_service in self.metrics:
            self.metrics[self.target_service].update(error_rate=42.0, latency_p95_ms=1800)

    async def run(self, log_callback):
        self.is_running = True
        while self.is_running:
            self.generate_baseline_metrics()
            self.apply_chaos_metrics()
            
            # Simulate high-volume logs: we only emit a sample to prevent overwhelming the UI
            active_svc = random.choice(SERVICES)
            log_callback(active_svc, "INFO", f"Processed request normally. latency={self.metrics[active_svc]['latency_p95_ms']}ms")
            
            if self.chaos_scenario:
                # Generate specific error logs
                if self.chaos_scenario == "payment_crash":
                    log_callback("paymentservice", "ERROR", "FATAL: PaymentService crashed: NullPointerException at payment connector")
                    log_callback("checkoutservice", "ERROR", "Payment failed for OrderID: 503 Service Unavailable API timeout")
                elif self.chaos_scenario == "frontend_spike":
                    log_callback("frontend", "ERROR", "503 Service Unavailable: overloaded, max connections reached")
                elif self.chaos_scenario == "payment_high_latency":
                    log_callback("paymentservice", "WARN", f"Payment request latency elevated: p95={self.metrics['paymentservice']['latency_p95_ms']}ms")
                elif self.chaos_scenario == "database_failure":
                    log_callback("database", "ERROR", "Database health check failed: connection refused; checkout and payment calls are timing out")
                elif self.chaos_scenario == "service_crash" and self.target_service:
                    log_callback(self.target_service, "ERROR", f"Health check failed: {self.target_service} is unavailable")
                elif self.chaos_scenario == "api_error_spike" and self.target_service:
                    log_callback(self.target_service, "ERROR", f"API error spike: elevated HTTP 5xx responses on {self.target_service}")
                elif self.chaos_scenario == "cpu_spike" and self.target_service:
                    log_callback(self.target_service, "ERROR", f"CPU spike: utilization reached 94% on {self.target_service}")
                elif self.chaos_scenario == "memory_spike" and self.target_service:
                    log_callback(self.target_service, "ERROR", f"Memory pressure: utilization reached 96% on {self.target_service}")
                elif self.chaos_scenario == "network_timeout" and self.target_service:
                    log_callback(self.target_service, "ERROR", f"Network timeout: upstream requests to {self.target_service} exceeded the deadline")

            await asyncio.sleep(1)

simulator = BoutiqueSimulator()
