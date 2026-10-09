# agents/remediation_agent.py

def determine_remediation(rca_output):
    """
    Remediation Agent determines the fix based on RCA.
    """
    issue = rca_output.get("root_cause", "").lower()
    
    service = rca_output.get("service", "paymentservice")

    if "database" in issue:
        return {
            "action": "restore_connection",
            "target": "database",
            "message": "Restore the database connection and verify dependent services."
        }

    if "cpu-saturated" in issue or "memory pressure" in issue:
        return {
            "action": "scale_deployment",
            "target": service,
            "replicas": 4,
            "message": f"Scale {service} from 2 to 4 replicas and verify resource pressure has cleared."
        }

    if "network deadline" in issue or "http 5xx" in issue or "elevated number of http" in issue:
        return {
            "action": "restart_service",
            "target": service,
            "message": f"Restart {service} and verify upstream connectivity and API responses."
        }

    if "unavailable" in issue or "health check" in issue:
        return {
            "action": "restart_service",
            "target": service,
            "message": f"Restart the {service} service and verify its health check."
        }

    if "latency" in issue or "saturated" in issue or "overloaded" in issue:
        return {
            "action": "scale_deployment",
            "target": service,
            "replicas": 4,
            "message": f"Scale {service} from 2 to 4 replicas to reduce request latency."
        }
        
    return {
        "action": "alert_only",
        "message": "Issue unknown. Paging human-in-the-loop."
    }
