# agents/rca_agent.py

def root_cause(log_summary, service):
    """
    RCA Agent utilizing Chain-of-Thought style pseudo-reasoning.
    Finds the root cause given structured logs.
    """
    evidence = log_summary.lower()
    if service == "database" or "databasefailure" in evidence or "database health check failed" in evidence:
        cause = "Database simulation is unavailable; dependent checkout and payment requests are timing out."
    elif "cpupressure" in evidence or "cpu spike" in evidence:
        cause = f"{service} is CPU-saturated, increasing processing time and error rates."
    elif "memorypressure" in evidence or "memory pressure" in evidence:
        cause = f"{service} is under memory pressure, reducing available capacity."
    elif "networktimeout" in evidence or "network timeout" in evidence:
        cause = f"Requests to {service} are exceeding their network deadline."
    elif "apierrorspike" in evidence or "api error spike" in evidence:
        cause = f"{service} is returning an elevated number of HTTP 5xx responses."
    elif "servicecrash" in evidence or "health check failed" in evidence or "crashed" in evidence:
        cause = f"{service} is unavailable after its health check failed."
    elif "latencydegradation" in evidence or "latency" in evidence or "timeout" in evidence or "overloaded" in evidence:
        cause = f"{service} is saturated and showing elevated request latency."
    else:
        cause = f"{service} is returning elevated errors and latency in the observed telemetry."
    return {
        "root_cause": cause,
        "evidence": log_summary,
        "service": service,
        "severity": "CRITICAL"
    }
