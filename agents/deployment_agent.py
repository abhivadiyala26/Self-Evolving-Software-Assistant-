# agents/deployment_agent.py

def execute_deployment(remediation_plan):
    """
    Mock Deployment Agent applying K8s fixes.
    """
    action = remediation_plan.get("action")
    target = remediation_plan.get("target")
    
    if action in {"restart_pod", "restart_service", "restart_simulation", "restore_connection", "reduce_load", "retry_request", "remove_bad_replica"}:
        if not target:
            return {"status": "failed", "message": "A target service is required for recovery."}
        return {
            "status": "success",
            "message": f"Applied bounded {action.replace('_', ' ')} action to {target}."
        }
        
    if action == "scale_deployment":
        replicas = int(remediation_plan.get("replicas", 3))
        if not target or replicas < 1 or replicas > 4:
            return {"status": "failed", "message": "Scaling is limited to one through four replicas and requires a target."}
        return {
            "status": "success",
            "message": f"Scaled {target} within the automatic limit to {replicas} replicas."
        }
    
    return {"status": "skipped", "message": "No k8s action required."}
