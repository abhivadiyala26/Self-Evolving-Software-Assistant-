def detect_anomaly(metrics_data):
    """Apply the demo monitor thresholds to a service health sample."""
    service = metrics_data.get("service", "service")
    violations = []
    if metrics_data.get("status", "healthy") != "healthy":
        violations.append(f"health={metrics_data['status']}")
    if metrics_data.get("latency", 0) >= 300:
        violations.append(f"p95 latency={metrics_data['latency']}ms")
    if metrics_data.get("errors", 0) >= 5:
        violations.append(f"error rate={metrics_data['errors']}%")
    if metrics_data.get("cpu", 0) >= 90:
        violations.append(f"CPU={metrics_data['cpu']}%")
    if metrics_data.get("memory", 0) >= 92:
        violations.append(f"memory={metrics_data['memory']}%")
    if metrics_data.get("requests_per_sec", 0) >= 1000:
        violations.append(f"traffic={metrics_data['requests_per_sec']} requests/sec")

    if violations:
        return {
            "status": "anomaly_detected",
            "message": f"Threshold breach on {service}: {', '.join(violations)}.",
            "signals": violations,
        }
    return {"status": "healthy", "message": f"{service} is within monitored health and telemetry thresholds.", "signals": []}
