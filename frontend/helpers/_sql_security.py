"""
SQL Security Testing Panel
- Testo SQL Injection live
- Shfaq risk level të çdo query
- Demonstro si sistemi bllokon sulmet
"""
import streamlit as st
import sys
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.security.sql_validator import validate_sql, sanitize_input, get_security_report, DANGEROUS_KEYWORDS, DANGEROUS_PATTERNS
from backend.security.audit_logger import log_event, get_logs


# ── Shembuj SQL Injection për demo ───────────────────────────────────────────
ATTACK_EXAMPLES = {
    "1. DROP TABLE (Fshirje të dhënash)": "SELECT * FROM fact_sales; DROP TABLE fact_sales;",
    "2. UNION Attack (Vjedhje të dhënash)": "SELECT * FROM fact_sales UNION SELECT username, password, null FROM users--",
    "3. OR 1=1 (Bypass Authentication)": "SELECT * FROM fact_sales WHERE region='Europe' OR 1=1--",
    "4. INSERT (Injektim të dhënash)": "INSERT INTO fact_sales VALUES ('fake', '2024-01-01', 100)",
    "5. EXEC (Ekzekutim komandash)": "EXEC xp_cmdshell('net user hacker password /add')",
    "6. Tabela e ndaluar": "SELECT * FROM users WHERE username='admin'",
    "7. Comment Attack": "SELECT * FROM fact_sales /* injected comment */ WHERE 1=1",
    "8. SLEEP Attack (DoS)": "SELECT * FROM fact_sales WHERE SLEEP(10)",
    "9. Query normale ✅": "SELECT region, SUM(revenue) FROM fact_sales GROUP BY region ORDER BY revenue DESC",
    "10. Query normale ✅": "SELECT year, quarter, SUM(profit) FROM fact_sales WHERE category='Electronics' GROUP BY year, quarter",
}


def show_sql_security_panel():
    """Paneli kryesor i testimit të sigurisë SQL."""

    st.markdown("## 🛡️ SQL Injection Prevention — Testim Live")
    st.caption("Demonstrim i mbrojtjes nga sulmet SQL Injection")

    # Tab layout
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧪 Testim Live",
        "📚 Llojet e Sulmeve",
        "📊 Statistikat",
        "🔍 Logs e Sulmeve"
    ])

    # ── TAB 1: Testim Live ───────────────────────────────────────────────────
    with tab1:
        st.markdown("### 🧪 Testo SQL Injection në Kohë Reale")
        st.info("Shkruaj ose zgjidh një SQL query dhe sistemi do analizojë rrezikun automatikisht.")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("**📝 Zgjidh shembull:**")
            selected = st.selectbox(
                "Shembuj të paracaktuar",
                list(ATTACK_EXAMPLES.keys()),
                label_visibility="collapsed"
            )
            if st.button("📋 Ngarko shembullin", use_container_width=True):
                st.session_state.sql_test_input = ATTACK_EXAMPLES[selected]

        sql_input = st.text_area(
            "SQL Query për testim:",
            value=st.session_state.get("sql_test_input", "SELECT * FROM fact_sales LIMIT 10"),
            height=120,
            key="sql_test_area"
        )

        if st.button("🔍 Analizo Sigurinë", type="primary", use_container_width=True):
            if sql_input.strip():
                _analyze_and_display(sql_input)

                # Log attempt
                username = st.session_state.get("username", "anonymous")
                report = get_security_report(sql_input)
                if not report["is_valid"]:
                    log_event(
                        username=username,
                        event_type="SQL_INJECTION_ATTEMPT",
                        details=f"SQL Injection detected: {report['message']}",
                        sql=sql_input,
                        success=False,
                        risk_level="CRITICAL" if report["risks"] else "HIGH"
                    )

    # ── TAB 2: Llojet e Sulmeve ──────────────────────────────────────────────
    with tab2:
        st.markdown("### 📚 Llojet e Sulmeve SQL Injection")

        attacks = [
            {
                "Lloji": "DROP/DELETE Attack",
                "Shpjegimi": "Sulmuesi përpiqet të fshijë tabela ose të dhëna",
                "Shembull": "'; DROP TABLE users;--",
                "Pasoja": "Humbje e të gjitha të dhënave",
                "Mbrojtja": "Blloko keywords DROP, DELETE"
            },
            {
                "Lloji": "UNION Attack",
                "Shpjegimi": "Kombinon rezultate nga tabela të ndryshme për të vjedhur të dhëna",
                "Shembull": "' UNION SELECT password FROM users--",
                "Pasoja": "Vjedhje fjalëkalimesh dhe të dhënash sensitive",
                "Mbrojtja": "Blloko UNION SELECT pattern"
            },
            {
                "Lloji": "OR 1=1 Attack",
                "Shpjegimi": "Anashkalon autentifikimin me kusht gjithmonë të vërtetë",
                "Shembull": "' OR '1'='1",
                "Pasoja": "Akses i paautorizuar në sistem",
                "Mbrojtja": "Detekto OR 1=1 pattern"
            },
            {
                "Lloji": "SLEEP/DoS Attack",
                "Shpjegimi": "Ngadalëson ose bllokon databazën",
                "Shembull": "'; SELECT SLEEP(10);--",
                "Pasoja": "Sistem i ngadaltë ose i bllokuar",
                "Mbrojtja": "Blloko SLEEP, BENCHMARK"
            },
            {
                "Lloji": "Comment Attack",
                "Shpjegimi": "Përdor komente SQL për të anashkaluar filtra",
                "Shembull": "SELECT * /* bypass */ FROM users",
                "Pasoja": "Anashkalim i mbrojtjeve",
                "Mbrojtja": "Detekto /* */ pattern"
            },
            {
                "Lloji": "EXEC Attack",
                "Shpjegimi": "Ekzekuton komanda sistemi përmes databazës",
                "Shembull": "EXEC xp_cmdshell('dir')",
                "Pasoja": "Kontroll i plotë i serverit",
                "Mbrojtja": "Blloko EXEC, xp_ procedura"
            },
        ]

        for attack in attacks:
            with st.expander(f"🔴 {attack['Lloji']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**📖 Shpjegimi:** {attack['Shpjegimi']}")
                    st.markdown(f"**💥 Pasoja:** {attack['Pasoja']}")
                with col2:
                    st.markdown("**🔴 Shembull sulmi:**")
                    st.code(attack["Shembull"], language="sql")
                    st.markdown(f"**🛡️ Mbrojtja:** {attack['Mbrojtja']}")

                if st.button(f"🧪 Testo këtë sulm", key=f"test_{attack['Lloji']}"):
                    st.session_state.sql_test_input = attack["Shembull"]
                    st.rerun()

    # ── TAB 3: Statistikat ───────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📊 Statistikat e Mbrojtjes")

        logs = get_logs(event_type="SQL_INJECTION_ATTEMPT", limit=500)
        all_logs = get_logs(limit=500)
        query_logs = get_logs(event_type="QUERY", limit=500)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🛡️ Sulme të Bllokuara", len(logs), delta="nga sistemi")
        col2.metric("✅ Queries të Sigurta", len(query_logs))
        col3.metric("📊 Total Events", len(all_logs))

        if len(query_logs) + len(logs) > 0:
            rate = round(len(logs) / (len(query_logs) + len(logs)) * 100, 1)
            col4.metric("⚠️ Shkalla e Sulmeve", f"{rate}%")
        else:
            col4.metric("⚠️ Shkalla e Sulmeve", "0%")

        st.divider()

        # Keywords më të përdorura
        st.markdown("**🔑 Keywords të Rrezikshme të Detektuara:**")
        keyword_counts = {}
        for log in logs:
            details = log.get("details", "")
            for kw in DANGEROUS_KEYWORDS:
                if kw in details.upper():
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        if keyword_counts:
            kw_df = pd.DataFrame([
                {"Keyword": k, "Tentativa": v}
                for k, v in sorted(keyword_counts.items(), key=lambda x: -x[1])
            ])
            st.dataframe(kw_df, use_container_width=True, hide_index=True)
        else:
            st.info("Asnjë sulm i regjistruar ende. Testo nga paneli 'Testim Live'!")

        # Mbrojtjet aktive
        st.markdown("**🛡️ Mbrojtjet Aktive:**")
        protections = [
            {"Mbrojtja": "Whitelist Keywords", "Statusi": "✅ Aktiv", "Detaje": f"{len(DANGEROUS_KEYWORDS)} keywords të bllokuara"},
            {"Mbrojtja": "Pattern Detection", "Statusi": "✅ Aktiv", "Detaje": f"{len(DANGEROUS_PATTERNS)} patterns të kontrolluara"},
            {"Mbrojtja": "Table Whitelist", "Statusi": "✅ Aktiv", "Detaje": "Vetëm 5 tabela të lejuara"},
            {"Mbrojtja": "SELECT Only", "Statusi": "✅ Aktiv", "Detaje": "Vetëm queries lexuese lejohen"},
            {"Mbrojtja": "Query Length Limit", "Statusi": "✅ Aktiv", "Detaje": "Max 5000 karaktere"},
            {"Mbrojtja": "Rate Limiting", "Statusi": "✅ Aktiv", "Detaje": "Max 50 queries/orë/user"},
            {"Mbrojtja": "Audit Logging", "Statusi": "✅ Aktiv", "Detaje": "Çdo sulm regjistrohet"},
        ]
        st.dataframe(pd.DataFrame(protections), use_container_width=True, hide_index=True)

    # ── TAB 4: Logs ──────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### 🔍 Logs e Tentativave SQL Injection")

        logs = get_logs(event_type="SQL_INJECTION_ATTEMPT", limit=100)

        if logs:
            st.error(f"🚨 {len(logs)} tentativa sulmi të detektuara!")
            df = pd.DataFrame(logs)[["timestamp", "username", "details", "risk_level"]]
            df.columns = ["Koha", "Përdoruesi", "Detajet", "Rreziku"]
            st.dataframe(df, use_container_width=True, height=300)

            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️ Eksporto Logs",
                csv,
                "sql_injection_logs.csv",
                "text/csv",
                key="export_sql_logs"
            )
        else:
            st.success("✅ Asnjë tentativë SQL Injection e regjistruar!")
            st.info("Përdor panelin 'Testim Live' për të simuluar sulme dhe parë si sistemi i bllokon.")


def _analyze_and_display(sql: str):
    """Analizo dhe shfaq rezultatin e sigurisë."""
    report = get_security_report(sql)
    is_valid = report["is_valid"]

    st.divider()
    st.markdown("### 📋 Rezultati i Analizës")

    # Rezultati kryesor
    if is_valid:
        st.success(f"✅ **QUERY E SIGURT** — {report['message']}")
    else:
        st.error(f"🚨 **SULM I DETEKTUAR DHE BLLOKUAR!**\n\n{report['message']}")

    # Detajet
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Risk Level", report["risk_level"],
                delta="⚠️ E lartë" if report["risk_level"] == "HIGH" else "✅ E ulët")
    col2.metric("Fillon me SELECT", "✅ Po" if report["starts_with_select"] else "❌ Jo")
    col3.metric("Gjatësia SQL", f"{report['sql_length']} chars")
    col4.metric("Rreziqe", len(report["risks"]))

    # Rreziqet e gjetur
    if report["risks"]:
        st.markdown("**🔴 Rreziqe të Gjetur:**")
        for risk in report["risks"]:
            severity = risk["severity"]
            color = "🔴" if severity == "CRITICAL" else "🟡"
            st.markdown(f"{color} **{severity}** — Tip: `{risk['type']}` — Vlera: `{risk['value']}`")

    # SQL i sanitizuar
    sanitized = sanitize_input(sql)
    if sanitized != sql:
        st.markdown("**🧹 Input i Sanitizuar (pas pastrimit):**")
        st.code(sanitized, language="sql")

    # Vizualizim i procesit
    st.markdown("**🔄 Procesi i Validimit:**")
    steps = [
        ("1. Kontrollo SELECT", sql.upper().strip().startswith(("SELECT", "WITH")), "Vetëm lexim lejohet"),
        ("2. Kërko keywords", len([k for k in DANGEROUS_KEYWORDS if k in sql.upper()]) == 0, "Asnjë keyword i rrezikshëm"),
        ("3. Kërko patterns", len(report["risks"]) == 0, "Asnjë pattern sulmi"),
        ("4. Kontrollo tabelat", is_valid, "Vetëm tabela të lejuara"),
        ("5. Kontrollo gjatësinë", len(sql) <= 5000, "Brenda limitit"),
    ]
    for step_name, passed, desc in steps:
        icon = "✅" if passed else "❌"
        st.markdown(f"{icon} **{step_name}** — {desc}")
