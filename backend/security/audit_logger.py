"""
Audit Logging & Monitoring Module
- Log çdo veprim të përdoruesit
- Detekto aktivitet të dyshimtë
- Eksporto logs
"""
import os
import json
from datetime import datetime
from typing import Optional

AUDIT_FILE = os.path.join(os.path.dirname(__file__), "audit_logs.json")


def _load_logs() -> list:
    if not os.path.exists(AUDIT_FILE):
        return []
    with open(AUDIT_FILE, "r") as f:
        return json.load(f)


def _save_logs(logs: list):
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=2)


def log_event(
    username: str,
    event_type: str,
    details: str,
    sql: Optional[str] = None,
    success: bool = True,
    risk_level: str = "LOW"
):
    """
    Regjistro event në audit log.

    event_type: LOGIN, LOGOUT, QUERY, SQL_INJECTION_ATTEMPT,
                USER_CREATED, USER_DELETED, EXPORT, ACCESS_DENIED
    """
    logs = _load_logs()

    log_entry = {
        "id": len(logs) + 1,
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "event_type": event_type,
        "details": details,
        "sql": sql[:200] if sql else None,  # Ruaj vetëm 200 karakteret e para
        "success": success,
        "risk_level": risk_level
    }

    logs.append(log_entry)

    # Ruaj vetëm 1000 logs të fundit
    if len(logs) > 1000:
        logs = logs[-1000:]

    _save_logs(logs)
    return log_entry


def get_logs(
    username: Optional[str] = None,
    event_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 100
) -> list:
    """Merr logs me filtra opsionalë."""
    logs = _load_logs()

    if username:
        logs = [l for l in logs if l["username"] == username]
    if event_type:
        logs = [l for l in logs if l["event_type"] == event_type]
    if risk_level:
        logs = [l for l in logs if l["risk_level"] == risk_level]

    # Ktheje në rend të kundërt (të fundit fillimisht)
    return list(reversed(logs))[:limit]


def get_statistics() -> dict:
    """Statistika të audit log."""
    logs = _load_logs()

    if not logs:
        return {
            "total_events": 0,
            "total_queries": 0,
            "failed_logins": 0,
            "security_alerts": 0,
            "active_users": 0
        }

    return {
        "total_events": len(logs),
        "total_queries": len([l for l in logs if l["event_type"] == "QUERY"]),
        "failed_logins": len([l for l in logs if l["event_type"] == "LOGIN" and not l["success"]]),
        "security_alerts": len([l for l in logs if l["risk_level"] in ("HIGH", "CRITICAL")]),
        "active_users": len(set(l["username"] for l in logs)),
        "sql_injection_attempts": len([l for l in logs if l["event_type"] == "SQL_INJECTION_ATTEMPT"]),
    }


def detect_suspicious_activity(username: str) -> list:
    """Detekto aktivitet të dyshimtë për një user."""
    logs = _load_logs()
    user_logs = [l for l in logs if l["username"] == username]

    alerts = []

    # 1. Shumë login të dështuara
    failed_logins = [l for l in user_logs if l["event_type"] == "LOGIN" and not l["success"]]
    if len(failed_logins) >= 3:
        alerts.append({
            "type": "BRUTE_FORCE",
            "message": f"⚠️ {len(failed_logins)} login të dështuara nga '{username}'",
            "severity": "HIGH"
        })

    # 2. SQL Injection attempts
    sql_attempts = [l for l in user_logs if l["event_type"] == "SQL_INJECTION_ATTEMPT"]
    if sql_attempts:
        alerts.append({
            "type": "SQL_INJECTION",
            "message": f"🚨 {len(sql_attempts)} tentativa SQL Injection nga '{username}'",
            "severity": "CRITICAL"
        })

    # 3. Shumë queries në kohë të shkurtër
    recent_queries = [l for l in user_logs if l["event_type"] == "QUERY"]
    if len(recent_queries) >= 20:
        alerts.append({
            "type": "HIGH_QUERY_RATE",
            "message": f"⚠️ {len(recent_queries)} queries nga '{username}' — aktivitet i lartë",
            "severity": "MEDIUM"
        })

    return alerts


def export_logs_csv() -> str:
    """Eksporto logs si CSV string."""
    logs = _load_logs()
    if not logs:
        return "No logs available"

    lines = ["ID,Timestamp,Username,Event Type,Details,Success,Risk Level"]
    for log in logs:
        lines.append(
            f"{log['id']},{log['timestamp']},{log['username']},"
            f"{log['event_type']},\"{log['details']}\","
            f"{log['success']},{log['risk_level']}"
        )
    return "\n".join(lines)
