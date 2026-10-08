# main.py
from fastapi import FastAPI, BackgroundTasks, Depends, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
import secrets

# Import agents
from agents.monitoring_agent import detect_anomaly
from agents.analysis_agent import analyze_logs
from agents.rca_agent import root_cause
from agents.remediation_agent import determine_remediation
from agents.deployment_agent import execute_deployment
from services.boutique_simulator import simulator
from services.incident_service import incident_manager, evaluate_severity, analyze_impact

app = FastAPI(title="AutoSRE Agent Backend")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulator.run(add_log))
    asyncio.create_task(background_monitor_loop())

# Allow CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    email: str
    password: str

class OrderRequest(BaseModel):
    items: list[dict]
    totalAmount: float
    paymentMethod: str
    address: str
    deliveryOption: str = "standard"

# In-memory store for demo logs to be polled by frontend
demo_logs = []
alerts = []
orders = []
admin_sessions = set()
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
}
monitor_violation_streaks = {}
processed_incidents = set()
processing_incidents = set()

def require_admin(x_admin_token: str = Header(default="")):
    if not x_admin_token or x_admin_token not in admin_sessions:
        raise HTTPException(status_code=403, detail="Admin authentication required.")
    return True

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
    alerts.insert(0, {
        "alert_id": f"ALT-{len(alerts) + 1:04d}",
        "service": service,
        "severity": severity,
        "title": title,
        "description": description,
        "incident_id": incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "firing"
    })
    del alerts[200:]


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
                violating = (
                    service["status"] != "healthy"
                    or values.get("error_rate", 0) >= 5
                    or values.get("latency_p95_ms", 0) >= 300
                    or values.get("cpu_percent", 0) >= 90
                    or values.get("memory_percent", 0) >= 92
                    or values.get("requests_per_sec", 0) >= 1000
                )
                monitor_violation_streaks[name] = monitor_violation_streaks.get(name, 0) + 1 if violating else 0

            active = incident_manager.get_active_incident()
            if not active:
                candidate = next((svc for svc in services if monitor_violation_streaks.get(svc["id"], 0) >= 3), None)
                if candidate:
                    name = candidate["id"]
                    current_system_state = "anomaly"
                    active = incident_manager.create_incident("telemetry_anomaly", name, metrics)
                    incident_id = active["incident_id"]
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
            background_agent["last_action"] = f"Monitor cycle error: {error}"
            add_log("Monitoring Agent", "Error", f"Background telemetry cycle failed: {error}")
        await asyncio.sleep(1)

@app.post("/api/auth/login")
async def admin_login(credentials: AdminLogin):
    # Demo credentials are deliberately fixed for the college demonstration.
    if simulator.service_states.get("authservice") != "healthy":
        raise HTTPException(status_code=503, detail="Authentication service is unavailable.")
    if credentials.email.lower() != "admin@technogear.com" or credentials.password != "password":
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
    token = secrets.token_urlsafe(32)
    admin_sessions.add(token)
    return {"token": token, "role": "admin", "name": "Admin"}

@app.post("/api/auth/logout")
async def admin_logout(admin: bool = Depends(require_admin), x_admin_token: str = Header(default="")):
    admin_sessions.discard(x_admin_token)
    return {"status": "logged_out"}

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
    orders.clear()
    current_system_state = "healthy"
    simulator.reset()
    incident_manager.reset()
    monitor_violation_streaks.clear()
    processed_incidents.clear()
    processing_incidents.clear()
    background_agent.update({"status": "running", "auto_recoveries": 0, "escalations": 0, "last_action": "Demo reset; monitoring resumed", "activity": []})
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

def classify_recovery_risk(scenario: str, service: str, metrics: dict, impact: dict) -> str:
    values = metrics.get(service, {})
    error_rate = values.get("error_rate", 0)
    latency = values.get("latency_p95_ms", 0)
    status = simulator.service_states.get(service, "healthy")
    affected = set(impact.get("directly_affected", [])) | set(impact.get("downstream_affected", []))
    active_affected = sum(
        1 for name in affected
        if simulator.service_states.get(name) != "healthy"
        or metrics.get(name, {}).get("error_rate", 0) >= 20
    )
    if scenario in {"database_failure", "payment_crash"} or latency >= 2500 or (service == "paymentservice" and error_rate >= 50) or active_affected >= 4:
        return "critical"
    if (status == "down" and service in {"authservice", "paymentservice", "checkoutservice", "database"}) or latency >= 1500 or error_rate >= 25 or (service == "database" and values.get("memory_percent", 0) >= 95) or active_affected >= 3:
        return "high"
    return "medium"


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
        add_log("Detection Agent", "Detection", f"Threshold policy matched for {svc}; severity evaluated as {dynamic_severity}.")

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

        risk_level = classify_recovery_risk(scenario, svc, all_metrics, impact)
        if incident_id:
            incident_manager.update_incident(incident_id, {
                "status": "awaiting_approval" if risk_level in {"high", "critical"} else "recovering",
                "approval_status": "pending" if risk_level in {"high", "critical"} else "not_required",
                "risk_level": risk_level,
                "recommended_remediation": remediation_plan.get("message", "Apply the recommended recovery action"),
                "recovery_action": remediation_plan
            })
            incident_manager.add_timeline_event(
                incident_id,
                stage="Remediation Strategy",
                title=f"{risk_level.title()}-risk remediation selected",
                description=f"{remediation_plan.get('message', 'Selected remediation strategy')} Risk policy: {risk_level}; {'administrator approval required' if risk_level in {'high', 'critical'} else 'bounded automatic recovery allowed'}.",
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
    incident = incident_manager.get_incident_by_id(incident_id)
    if not incident or generation != runtime_generation:
        return
    plan = incident.get("recovery_action") or {"action": "restart_simulation", "target": "all"}
    target = plan.get("target") or (incident.get("affected_services", {}).get("directly_affected") or ["frontend"])[0]
    max_attempts = 3 if automatic else 1
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
            if action == "scale_deployment" and not simulator.scale_service(target, min(4, max(1, int(plan.get("replicas", 3))))):
                result = {"status": "failed", "message": "Scaling policy rejected the requested replica count; automatic limit is four."}
            elif action in {"restart_service", "restart_simulation", "restart_pod", "restore_connection", "reduce_load", "retry_request", "remove_bad_replica", "scale_deployment"}:
                simulator.recover_service(target)
            else:
                result = {"status": "failed", "message": result.get("message", "No safe recovery action was available.")}

        if result.get("status") == "success":
            incident_manager.update_incident(incident_id, {"executed_action": result.get("message"), "recovery_status": "verifying"})
            incident_manager.add_timeline_event(incident_id, "Recovery Execution", f"{label.title()} recovery executed", result.get("message", "Recovery action applied."), "Recovery Agent")
            add_log("Recovery Agent", "Action", result.get("message", "Recovery action applied."))
            current_system_state = "recovering"
            await asyncio.sleep(2.2)
            if generation != runtime_generation:
                return

            health = simulator.get_services()
            metrics = simulator.get_metrics()
            healthy = all(service["status"] == "healthy" for service in health)
            metrics_ok = all(values["error_rate"] < 5 and values["latency_p95_ms"] < 800 for values in metrics.values())
            if healthy and metrics_ok:
                incident_manager.add_timeline_event(incident_id, "Verification", "Post-recovery health check passed", "Service health, latency, and error rates remained within recovery thresholds for two monitor cycles.", "Verification Agent")
                add_log("Verification Agent", "Health Check", "Recovery verified: services are healthy and telemetry is within baseline limits.")
                incident_manager.update_incident(incident_id, {"auto_recovered": automatic, "approval_status": "not_required" if automatic else "approved"})
                incident_manager.resolve_incident(incident_id, f"{label.title()} recovery completed and post-recovery checks passed.")
                for alert in alerts:
                    if alert.get("incident_id") == incident_id:
                        alert["status"] = "resolved"
                if automatic:
                    background_agent["auto_recoveries"] += 1
                background_agent["last_action"] = f"Recovered {target}; verification passed"
                current_system_state = "healthy"
                return
            result = {"status": "failed", "message": "Post-recovery health checks did not pass."}

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
            "recommended_remediation": f"Three bounded automatic recovery attempts failed. Review and approve: {plan.get('message', plan.get('action'))}",
        })
        incident_manager.add_timeline_event(incident_id, "Escalation", "Automatic recovery limit reached", "Three automatic recovery attempts failed; an administrator must review the next action.", "Incident Manager Agent")
        background_agent["escalations"] += 1
        background_agent["last_action"] = f"Escalated {incident_id} after three failed automatic attempts"
        current_system_state = "awaiting_approval"
        add_log("Incident Manager Agent", "Approval", f"Incident {incident_id} escalated after three failed automatic recovery attempts; administrator approval is required.")
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
    simulator.reset()
    current_system_state = "healthy"
    incident = incident_manager.get_active_incident()
    if incident:
        incident_manager.update_incident(incident["incident_id"], {"approval_status": "manual_recovery", "auto_recovered": False, "executed_action": f"Administrator restarted {service}."})
        incident_manager.add_timeline_event(incident["incident_id"], "Admin Recovery", "Service restarted", f"Administrator restarted {service}.", "Admin")
        incident_manager.add_timeline_event(incident["incident_id"], "Verification", "Health check passed", "The simulator reports all services healthy.", "Verification Agent")
        incident_manager.resolve_incident(incident["incident_id"], "Administrator restarted the service and health checks passed.")
    add_log("Admin", "Recovery", f"Administrator started {service}.")
    return {"status": "healthy", "service": service}

@app.get("/api/orders")
async def get_orders():
    return orders

async def progress_order(order_id: str):
    stages = ["CONFIRMED", "PACKED", "SHIPPED", "OUT FOR DELIVERY", "DELIVERED"]
    for stage in stages:
        await asyncio.sleep(3)
        order = next((item for item in orders if item["order_id"] == order_id), None)
        if not order:
            return
        order["status"] = stage
        add_log("Order Service", "Order Update", f"Order {order_id} status changed to {stage}.")

@app.post("/api/orders")
async def place_order(order: OrderRequest):
    if simulator.service_states.get("paymentservice") != "healthy" or simulator.service_states.get("checkoutservice") != "healthy":
        raise HTTPException(status_code=503, detail="Checkout is temporarily unavailable while payment services recover.")
    if not order.items:
        raise HTTPException(status_code=422, detail="Your cart is empty.")
    now = datetime.now(timezone.utc)
    record = {
        "order_id": f"AS-{now.strftime('%y%m%d')}-{len(orders) + 1:04d}",
        "items": order.items,
        "totalAmount": round(order.totalAmount, 2),
        "paymentMethod": order.paymentMethod,
        "paymentStatus": "pending" if order.paymentMethod.upper() == "COD" else "paid",
        "status": "PLACED",
        "address": order.address,
        "timestamp": now.isoformat(),
        "deliveryOption": order.deliveryOption,
        "deliveryEstimate": "Today by 9 PM" if order.deliveryOption == "express" else "Delivery by Tomorrow"
    }
    orders.insert(0, record)
    add_log("Order Service", "Order", f"Order {record['order_id']} placed for ₹{record['totalAmount']:,.2f}.")
    task = asyncio.create_task(progress_order(record["order_id"]))
    order_progress_tasks.add(task)
    task.add_done_callback(order_progress_tasks.discard)
    return {"order": record}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
