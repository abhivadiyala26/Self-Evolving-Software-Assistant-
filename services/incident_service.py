# services/incident_service.py
import time
from datetime import datetime
import threading

# Centralized Service Dependency Graph
DEPENDENCY_GRAPH = {
    "authservice": ["frontend"],
    "paymentservice": ["checkoutservice", "frontend"],
    "cartservice": ["frontend"],
    "shippingservice": ["checkoutservice", "frontend"],
    "currencyservice": ["frontend"],
    "recommendationservice": ["frontend"],
    "productcatalogservice": ["frontend"],
    "adservice": ["frontend"],
    "emailservice": ["checkoutservice"],
    "checkoutservice": ["frontend"],
    "database": ["checkoutservice", "paymentservice"],
    "frontend": []
}

CRITICAL_SERVICES = {"authservice", "paymentservice", "checkoutservice", "frontend", "database"}

def analyze_impact(primary_service: str) -> dict:
    """Returns directly affected and downstream affected services."""
    downstream = DEPENDENCY_GRAPH.get(primary_service, [])
    return {
        "directly_affected": [primary_service] if primary_service else [],
        "downstream_affected": downstream
    }

def evaluate_severity(metrics: dict, primary_service: str, affected_impact: dict) -> str:
    """
    Dynamically evaluates incident severity (P1-P4) based on telemetry and impact analysis.
    P1 = Critical user-facing or financial service failure (high error rate > 50% or latency > 2000ms)
    P2 = Major degradation (error rate > 20% or latency > 800ms or multiple downstream impacts)
    P3 = Moderate anomaly (error rate > 5% or latency > 300ms)
    P4 = Minor anomaly
    """
    svc_metrics = metrics.get(primary_service, {}) if metrics else {}
    error_rate = svc_metrics.get("error_rate", 0.0)
    latency = svc_metrics.get("latency_p95_ms", 0)
    cpu = svc_metrics.get("cpu_percent", 0)
    memory = svc_metrics.get("memory_percent", 0)
    requests_per_sec = svc_metrics.get("requests_per_sec", 0)

    is_critical_svc = primary_service in CRITICAL_SERVICES

    if (error_rate > 50.0 or latency > 2000) or (is_critical_svc and error_rate > 30.0):
        return "P1"
    elif error_rate > 20.0 or latency > 800 or cpu >= 90 or memory >= 92 or requests_per_sec >= 1000 or len(affected_impact.get("downstream_affected", [])) >= 2:
        return "P2"
    elif error_rate > 5.0 or latency > 300:
        return "P3"
    return "P4"

class IncidentManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.incidents = []
        self.active_incident_id = None
        self.counter = 1

    def _get_timestamp_str(self) -> str:
        return datetime.now().strftime("%I:%M:%S %p")

    def create_incident(self, scenario: str, primary_service: str = None, current_metrics: dict = None) -> dict:
        with self._lock:
            incident_id = f"INC-2026-{self.counter:03d}"
            self.counter += 1

            if not primary_service:
                primary_service = "paymentservice" if scenario == "payment_crash" else "frontend"

            impact = analyze_impact(primary_service)
            initial_severity = evaluate_severity(current_metrics or {}, primary_service, impact)

            now_str = self._get_timestamp_str()
            now_epoch = time.time()

            incident = {
                "incident_id": incident_id,
                "timestamp": now_str,
                "start_time": now_str,
                "start_timestamp": now_epoch,
                "scenario": scenario,
                "severity": initial_severity,
                "risk_level": "assessing",
                "status": "investigating",
                "approval_status": "not_required",
                "recovery_attempts": 0,
                "auto_recovered": False,
                "affected_services": impact,
                "symptoms": f"Elevated error rates and latency in {primary_service}",
                "root_cause": "Under investigation by AI Agents...",
                "evidence": "Telemetry anomaly detected.",
                "recommended_remediation": "Pending analysis...",
                "recovery_action": None,
                "executed_action": "None",
                "recovery_status": "investigating",
                "detection_time": None,
                "resolution_time": None,
                "total_duration": None,
                "timeline": [
                    {
                        "timestamp": now_str,
                        "stage": "Chaos Trigger",
                        "title": "Chaos Scenario Triggered",
                        "description": f"Failure scenario '{scenario}' injected into system.",
                        "agent": "System"
                    }
                ]
            }

            self.incidents.insert(0, incident) # newest first
            self.active_incident_id = incident_id
            return incident

    def add_timeline_event(self, incident_id: str, stage: str, title: str, description: str, agent: str = "System"):
        with self._lock:
            incident = self._find_incident(incident_id)
            if incident:
                incident["timeline"].append({
                    "timestamp": self._get_timestamp_str(),
                    "stage": stage,
                    "title": title,
                    "description": description,
                    "agent": agent
                })

    def update_incident(self, incident_id: str, updates: dict):
        with self._lock:
            incident = self._find_incident(incident_id)
            if incident:
                for k, v in updates.items():
                    incident[k] = v

    def resolve_incident(self, incident_id: str, recovery_message: str = "System returned to normal operational baseline."):
        with self._lock:
            incident = self._find_incident(incident_id)
            if incident:
                now_epoch = time.time()
                now_str = self._get_timestamp_str()
                start_epoch = incident.get("start_timestamp", now_epoch)
                duration_sec = int(max(1, now_epoch - start_epoch))

                incident["status"] = "resolved"
                incident["approval_status"] = "not_required" if incident.get("auto_recovered") else incident.get("approval_status", "pending")
                incident["recovery_status"] = "resolved"
                incident["resolution_time"] = now_str
                incident["total_duration"] = duration_sec
                incident["timeline"].append({
                    "timestamp": now_str,
                    "stage": "Incident Closure",
                    "title": "Incident Resolved",
                    "description": f"{recovery_message} Total Duration: {duration_sec}s.",
                    "agent": "System"
                })
                if self.active_incident_id == incident_id:
                    self.active_incident_id = None

    def fail_incident(self, incident_id: str, error_message: str):
        with self._lock:
            incident = self._find_incident(incident_id)
            if incident:
                now_epoch = time.time()
                now_str = self._get_timestamp_str()
                start_epoch = incident.get("start_timestamp", now_epoch)
                duration_sec = int(max(1, now_epoch - start_epoch))

                incident["status"] = "remediation_failed"
                incident["recovery_status"] = "failed"
                incident["resolution_time"] = now_str
                incident["total_duration"] = duration_sec
                incident["executed_action"] = f"FAILED: {error_message}"
                incident["timeline"].append({
                    "timestamp": now_str,
                    "stage": "Remediation Failure",
                    "title": "Remediation Execution Failed",
                    "description": f"CRITICAL: {error_message}. Human intervention required.",
                    "agent": "System"
                })
                if self.active_incident_id == incident_id:
                    self.active_incident_id = None

    def get_active_incident(self) -> dict:
        with self._lock:
            if not self.active_incident_id:
                return None
            return self._find_incident(self.active_incident_id)

    def get_all_incidents(self) -> list:
        with self._lock:
            return list(self.incidents)

    def get_incident_by_id(self, incident_id: str) -> dict:
        with self._lock:
            return self._find_incident(incident_id)

    def reset(self):
        with self._lock:
            self.active_incident_id = None
            self.incidents.clear()
            self.counter = 1

    def _find_incident(self, incident_id: str) -> dict:
        for inc in self.incidents:
            if inc["incident_id"] == incident_id:
                return inc
        return None

incident_manager = IncidentManager()
