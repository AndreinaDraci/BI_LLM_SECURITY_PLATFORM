"""
Zero Trust Dashboard — Streamlit Panel
=======================================
Vizualizim real-time i gjendjes Zero Trust:
- Policy decisions (Allow/Deny)
- Agent access log
- Active sessions
- Security alerts
- Least privilege violations
"""
import streamlit as st
import sys
import os
import pandas as pd
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def show_zero_trust_dashboard():
    """Zero Trust Dashboard — vetëm për Admin."""

    st.markdown("## 🔐 Zero Trust Dashboard")
    st.caption(
        "Monitorim real-time i arkitekturës Zero Trust — "
        "**Never Trust, Always Verify**"
    )

    # ── Importo komponentët Zero Trust ───────────────────────────────────────
    try:
        from backend.security.zero_trust_pep import zero_trust_pep
        from backend.security.policy_engine import (
            policy_engine, ROLE_POLICIES, AGENT_POLICIES,
            Resource, Action
        )
        zt_available = True
    except Exception as e:
        st.error(f"Zero Trust modules nuk u ngarkuan: {e}")
        zt_available = False

    if not zt_available:
        return

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🔍 Policy Decisions",
        "🤖 Agent Permissions",
        "🛡️ Security Matrix",
        "🧪 Live Test",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### 📊 Gjendja e Zero Trust")

        # Principet Zero Trust
        principles = [
            ("🚫", "Never Trust", "Asnjë entitet nuk besohet automatikisht"),
            ("✅", "Always Verify", "Çdo kërkesë verifikohet — vazhdimisht"),
            ("🔒", "Least Privilege", "Çdo komponent ka vetëm akseset minimale"),
            ("📋", "Assume Breach", "Sistemi supozohet i komprometuar gjithnjë"),
        ]

        cols = st.columns(4)
        for i, (icon, title, desc) in enumerate(principles):
            with cols[i]:
                st.markdown(f"""
                <div style="background:#1F3864; border-radius:8px; padding:12px; text-align:center; border:1px solid #2E75B6;">
                    <div style="font-size:1.8rem;">{icon}</div>
                    <div style="color:#58a6ff; font-weight:bold; font-size:0.85rem; margin:4px 0;">{title}</div>
                    <div style="color:#8b949e; font-size:0.75rem;">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # Statistikat
        stats = zero_trust_pep.get_zero_trust_stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Total Allowed", stats.get("allowed", 0))
        c2.metric("❌ Total Denied", stats.get("denied", 0))
        c3.metric("⚠️ Denial Rate", f"{stats.get('denial_rate', 0)}%")
        c4.metric("🚨 Alert Users", len(stats.get("users_with_alerts", [])))

        # Alert users
        alert_users = stats.get("users_with_alerts", [])
        if alert_users:
            st.error(f"🚨 Users me aktivitet të dyshimtë: **{', '.join(alert_users)}**")

        # Fluksi Zero Trust
        st.markdown("### 🔄 Fluksi Zero Trust")
        st.markdown("""
        ```
        USER REQUEST
             │
             ▼
        ┌─────────────────────────────────────────┐
        │   POLICY ENFORCEMENT POINT (PEP)        │
        │   1. Identity Verification (JWT)         │
        │   2. Continuous Authentication           │
        │   3. Policy Engine Check                 │
        │   4. RBAC Evaluation                     │
        └──────────────┬──────────────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
           ALLOW              DENY
              │                 │
              ▼                 ▼
        ┌──────────┐     ┌──────────────┐
        │ PLANNER  │     │  AUDIT LOG   │
        │          │     │  + ALERT     │
        └────┬─────┘     └──────────────┘
             │
        ┌────▼──────────────────────────┐
        │  AGENT AUTHORIZATION (PEP)    │
        │  Least Privilege Check        │
        └────┬──────────────────────────┘
             │
        ┌────▼──────────────┐
        │  SQL VALIDATOR    │
        └────┬──────────────┘
             │
        ┌────▼──────────────┐
        │  DuckDB (READ)    │
        └────┬──────────────┘
             │
        ┌────▼──────────────────────────┐
        │  OUTPUT VALIDATOR             │
        │  Data sanitization + redact   │
        └────┬──────────────────────────┘
             │
             ▼
        USER RESPONSE + AUDIT LOG
        ```
        """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — POLICY DECISIONS
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 🔍 Vendimet e Policy Engine")
        st.caption("Çdo Allow/Deny i dokumentuar me arsyetim")

        decisions = policy_engine.get_recent_decisions(50)

        if decisions:
            df = pd.DataFrame(decisions)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s').dt.strftime('%H:%M:%S')
            df['status'] = df['allowed'].apply(lambda x: '✅ ALLOW' if x else '❌ DENY')

            # Filtra
            col1, col2 = st.columns(2)
            with col1:
                filter_status = st.selectbox(
                    "Filtro sipas statusit",
                    ["Të gjitha", "ALLOW", "DENY"]
                )
            with col2:
                filter_risk = st.selectbox(
                    "Filtro sipas rrezikut",
                    ["Të gjitha", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
                )

            filtered = df.copy()
            if filter_status == "ALLOW":
                filtered = filtered[filtered['allowed'] == True]
            elif filter_status == "DENY":
                filtered = filtered[filtered['allowed'] == False]
            if filter_risk != "Të gjitha":
                filtered = filtered[filtered['risk_level'] == filter_risk]

            st.dataframe(
                filtered[['timestamp', 'username', 'role', 'resource',
                           'action', 'status', 'risk_level', 'reason']],
                use_container_width=True,
                height=350,
            )
        else:
            st.info("Asnjë vendim i regjistruar ende. Bëj disa operacione dhe kthehu këtu!")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — AGENT PERMISSIONS (LEAST PRIVILEGE)
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 🤖 Least Privilege — Permisionet e Agjentëve")
        st.caption(
            "Çdo agjent ka vetëm akseset minimale të nevojshme — "
            "Zero Trust Least Privilege"
        )

        agent_data = []
        for agent, policy in AGENT_POLICIES.items():
            agent_data.append({
                "Agjenti": agent,
                "Akses DB": "✅" if policy.get("can_access_db") else "❌",
                "Modifiko DB": "✅" if policy.get("can_modify_data") else "❌",
                "Thirr Agjentë": len(policy.get("can_access_agents", [])),
                "Tabela të Lejuara": ", ".join(policy.get("allowed_tables", ["N/A"])),
                "Operacione SQL": ", ".join(policy.get("allowed_operations", ["N/A"])),
            })

        df_agents = pd.DataFrame(agent_data)
        st.dataframe(df_agents, use_container_width=True, hide_index=True)

        st.info(
            "💡 **Least Privilege**: Report Generator dhe Visualization Agent **nuk** kanë "
            "akses direkt në DuckDB — marrin vetëm rezultatet nga agjentët e tjerë."
        )

        # Vizualizim i komunikimit inter-agent
        st.markdown("### 🔗 Komunikimi i Autorizuar ndër-Agjentë")
        st.markdown("""
        ```
        Planner ──────► Dimension Navigator  ──► DuckDB (READ only)
               │
               ├──────► Cube Operations      ──► DuckDB (READ only)
               │
               ├──────► KPI Calculator       ──► DuckDB (READ only, fact_sales)
               │
               ├──────► Anomaly Detection    ──► DuckDB (READ only, fact_sales)
               │
               ├──────► Report Generator     ──► ❌ NO DuckDB access
               │                                  (vetëm merr rezultate)
               │
               └──────► Visualization Agent  ──► ❌ NO DuckDB access
                                                  (vetëm merr rezultate)

        ⚠️  Agjentët NUK mund të thërrasin njëri-tjetrin direkt
        ⚠️  Vetëm Planner koordinon komunikimin
        ⚠️  Asnjë agjent nuk mund të SHKRUAJË në DuckDB
        ```
        """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — SECURITY MATRIX
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### 🛡️ Matrica e Sigurisë — Role vs Resurse")
        st.caption("Zero Trust Policy Matrix: çdo kombinim rol-resurs-veprim")

        matrix_data = []
        resources_display = {
            Resource.QUERY_OLAP:     "Query OLAP",
            Resource.QUERY_SQL_RAW:  "SQL Raw",
            Resource.DATA_EXPORT:    "Eksport CSV",
            Resource.DATA_ALL:       "Të dhëna të plota",
            Resource.AUDIT_VIEW:     "Audit Log",
            Resource.USER_MANAGE:    "Menaxho Users",
            Resource.AGENT_PLANNER:  "Planner Agent",
            Resource.DB_READ:        "Database Read",
            Resource.DB_WRITE:       "Database Write",
            Resource.SECURITY_PANEL: "Security Panel",
        }

        for resource, display_name in resources_display.items():
            row = {"Resursi": display_name}
            for role in ["admin", "analyst", "viewer"]:
                policy = ROLE_POLICIES.get(role, {})
                actions = policy.get(resource, [])
                if actions:
                    row[role.upper()] = "✅ " + "+".join([a.value for a in actions])
                else:
                    row[role.upper()] = "❌ Refuzuar"
            matrix_data.append(row)

        df_matrix = pd.DataFrame(matrix_data)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — LIVE TEST
    # ══════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("### 🧪 Testim Live i Zero Trust")
        st.caption("Testo Policy Engine direkt — shiko vendimin në kohë reale")

        col1, col2 = st.columns(2)
        with col1:
            test_role = st.selectbox("Roli", ["admin", "analyst", "viewer"])
            test_resource = st.selectbox(
                "Resursi",
                [r.value for r in Resource],
            )
        with col2:
            test_action = st.selectbox("Veprimi", [a.value for a in Action])
            test_username = st.text_input("Username (demo)", value="test_user")

        if st.button("🔍 Testo Policy", type="primary", use_container_width=True):
            from backend.security.policy_engine import (
                RequestContext, Resource as R, Action as A
            )

            # Gjej resource dhe action
            try:
                resource_enum = R(test_resource)
                action_enum = A(test_action)
            except ValueError:
                st.error("Resurs ose veprim i pavlefshëm")
                st.stop()

            ctx = RequestContext(
                username=test_username,
                role=test_role,
                token="demo_token",
                resource=resource_enum,
                action=action_enum,
                timestamp=time.time(),
            )

            # Evaluo direkt në Policy Engine (pa JWT check)
            decision = policy_engine.evaluate(ctx)

            if decision.allowed:
                st.success(f"✅ **ALLOW** — {decision.reason}")
            else:
                st.error(f"❌ **DENY** — {decision.reason}")

            st.json({
                "role": test_role,
                "resource": test_resource,
                "action": test_action,
                "allowed": decision.allowed,
                "risk_level": decision.risk_level,
                "constraints": decision.constraints,
            })

        # Test agjentësh
        st.divider()
        st.markdown("**🤖 Testo Least Privilege për Agjentë**")

        col1, col2 = st.columns(2)
        with col1:
            test_agent = st.selectbox("Agjenti", list(AGENT_POLICIES.keys()))
        with col2:
            test_target = st.selectbox(
                "Target",
                ["database", "agent:Report Generator", "agent:KPI Calculator",
                 "agent:Dimension Navigator"]
            )

        if st.button("🤖 Testo Agent Permission", use_container_width=True):
            decision = zero_trust_pep.enforce_agent_access(
                agent_name=test_agent,
                target_resource=test_target,
                action="read",
                context_username="admin_test",
            )

            if decision.allowed:
                st.success(f"✅ **ALLOW** — {decision.reason}")
            else:
                st.warning(f"⛔ **DENY (Least Privilege)** — {decision.reason}")
