"""Shared risk policy for safe automatic recovery versus human approval."""

import os


def _read_number(name: str, default: float, minimum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


WARNING_LATENCY_MS = _read_number("AUTOSRE_WARNING_LATENCY_MS", 300, 1)
CRITICAL_LATENCY_MS = _read_number("AUTOSRE_CRITICAL_LATENCY_MS", 500, WARNING_LATENCY_MS)
CRITICAL_ERROR_RATE_PERCENT = _read_number("AUTOSRE_CRITICAL_ERROR_RATE_PERCENT", 20, 1)
CRITICAL_WINDOW_SECONDS = _read_number("AUTOSRE_CRITICAL_WINDOW_SECONDS", 15, 1)
SAFE_REPLICA_LIMIT = min(4, int(_read_number("AUTOSRE_SAFE_REPLICA_LIMIT", 4, 1)))
AUTOMATIC_RECOVERY_ATTEMPTS = min(5, int(_read_number("AUTOSRE_AUTOMATIC_RECOVERY_ATTEMPTS", 3, 1)))
MAX_AUTOMATIC_IMPACTED_SERVICES = int(_read_number("AUTOSRE_MAX_AUTOMATIC_IMPACTED_SERVICES", 2, 1))

SAFE_AUTOMATIC_ACTIONS = {
    "restart_service",
    "restart_pod",
    "restore_connection",
    "reduce_load",
    "retry_request",
    "remove_bad_replica",
    "scale_deployment",
}
DESTRUCTIVE_ACTIONS = {
    "delete_database",
    "drop_database",
    "truncate_database",
    "delete_data",
    "replace_cluster",
}


def classify_recovery_risk(
    *,
    action: str,
    target: str | None,
    plan: dict,
    impacted_services: set[str],
    previous_attempts: int = 0,
    critical_sustained: bool = False,
) -> str:
    """Classify the proposed operation, independent of incident severity/type."""
    if action in DESTRUCTIVE_ACTIONS:
        return "critical"
    if action not in SAFE_AUTOMATIC_ACTIONS or not target:
        return "high"
    if previous_attempts >= AUTOMATIC_RECOVERY_ATTEMPTS:
        return "high"
    if len(impacted_services) > MAX_AUTOMATIC_IMPACTED_SERVICES:
        return "high"
    if action == "scale_deployment":
        # Sustained critical latency needs a control-plane decision even when
        # the requested replica count is inside the ordinary automatic bound.
        if critical_sustained:
            return "high"
        try:
            replicas = int(plan.get("replicas", 2))
        except (TypeError, ValueError):
            return "high"
        if replicas > SAFE_REPLICA_LIMIT or replicas < 1:
            return "high"
    return "medium"


def critical_metrics_sustained(values: dict, latency_duration: float = 0, error_duration: float = 0) -> bool:
    return (
        values.get("latency_p95_ms", 0) >= CRITICAL_LATENCY_MS
        and latency_duration >= CRITICAL_WINDOW_SECONDS
    ) or (
        values.get("error_rate", 0) >= CRITICAL_ERROR_RATE_PERCENT
        and error_duration >= CRITICAL_WINDOW_SECONDS
    )
