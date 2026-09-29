"""
Audit Dashboard Page – vetëm për Admin
"""
import streamlit as st
import sys
import os
import pandas as pd

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(FRONTEND_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.security.audit_logger import get_logs, get_statistics, detect_suspicious_activity, export_logs_csv


def show_audit_dashboard():
    """Audit Dashboard — vetëm për Admin."""

    st.markdown("## 🔍 Audit Log Dashboard")
    st.caption("Monitorim i aktivitetit të sistemit në kohë reale")

    # Statistikat
    stats = get_statistics()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Total Events", stats["total_events"])
    col2.metric("🔍 Total Queries", stats["total_queries"])
    col3.metric("❌ Failed Logins", stats["failed_logins"])
    col4.metric("🚨 Security Alerts", stats["security_alerts"])

    st.divider()

    # Filtra
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox("Event Type", [
            "Të gjitha", "LOGIN", "LOGOUT", "QUERY",
            "SQL_INJECTION_ATTEMPT", "USER_CREATED", "ACCESS_DENIED"
        ])
    with col2:
        filter_risk = st.selectbox("Risk Level", ["Të gjitha", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
    with col3:
        filter_user = st.text_input("Filtro sipas username")

    # Merr logs
    logs = get_logs(
        username=filter_user if filter_user else None,
        event_type=filter_type if filter_type != "Të gjitha" else None,
        risk_level=filter_risk if filter_risk != "Të gjitha" else None,
        limit=200
    )

    if logs:
        df = pd.DataFrame(logs)

        # Formatim
        def color_risk(val):
            colors = {
                "CRITICAL": "background-color: #da363360",
                "HIGH": "background-color: #e3b34160",
                "MEDIUM": "background-color: #1f6feb60",
                "LOW": "background-color: #3fb95030"
            }
            return colors.get(val, "")

        st.dataframe(
            df[["timestamp", "username", "event_type", "details", "success", "risk_level"]],
            use_container_width=True,
            height=400
        )

        # Export
        csv = export_logs_csv()
        st.download_button(
            "⬇️ Eksporto Logs (CSV)",
            csv,
            "audit_logs.csv",
            "text/csv",
            key="export_audit"
        )

        # Suspicious activity
        st.markdown("### 🚨 Aktivitet i Dyshimtë")
        users = list(set(l["username"] for l in logs))
        for user in users:
            alerts = detect_suspicious_activity(user)
            for alert in alerts:
                if alert["severity"] == "CRITICAL":
                    st.error(alert["message"])
                elif alert["severity"] == "HIGH":
                    st.warning(alert["message"])
                else:
                    st.info(alert["message"])

        if not any(detect_suspicious_activity(u) for u in users):
            st.success("✅ Nuk u detektua asnjë aktivitet i dyshimtë!")

    else:
        st.info("Nuk ka logs ende. Bëj disa veprime dhe kthehu këtu!")
