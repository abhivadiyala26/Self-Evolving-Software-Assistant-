# agents/analysis_agent.py

def analyze_logs(logs_context):
    """
    Log Analysis Agent setup using Langchain pseudo-logic.
    Extracts structured data from raw log dumps.
    """
    prompt_thought = "Thinking: Analyzing the raw log dump from the anomalous timeframe step-by-step..."
    
    # Dynamically find the service from our simulator list
    services = ["frontend", "authservice", "cartservice", "checkoutservice", "recommendationservice",
                "productcatalogservice", "paymentservice", "shippingservice", "database",
                "emailservice", "currencyservice", "adservice", "loadgenerator"]
    
    impacted_svc = "unknown"
    for svc in services:
        if svc in logs_context.lower():
            impacted_svc = svc
            break
            
    if impacted_svc != "unknown":
        lower_logs = logs_context.lower()
        error_type = "ServiceDegradation"
        if "cpu spike" in lower_logs or "cpu pressure" in lower_logs:
            error_type = "CpuPressure"
        elif "memory pressure" in lower_logs or "memory spike" in lower_logs:
            error_type = "MemoryPressure"
        elif "network timeout" in lower_logs:
            error_type = "NetworkTimeout"
        elif "api error spike" in lower_logs or "http 5xx" in lower_logs:
            error_type = "ApiErrorSpike"
        elif "crashed" in lower_logs or "health check failed" in lower_logs or "unavailable" in lower_logs:
            error_type = "ServiceCrash"
        elif "latency" in lower_logs or "timeout" in lower_logs:
            error_type = "LatencyDegradation"
        elif "database" in lower_logs or impacted_svc == "database":
            error_type = "DatabaseFailure"
        return {
            "summary": f"{impacted_svc.capitalize()} service {error_type.lower()} detected in observed logs: {logs_context[-500:]}",
            "impacted_service": impacted_svc,
            "error_type": error_type,
            "thought_process": prompt_thought
        }
        
    return {
        "summary": "No specific critical error patterns detected.",
        "impacted_service": "unknown",
        "error_type": "None",
        "thought_process": prompt_thought
    }
