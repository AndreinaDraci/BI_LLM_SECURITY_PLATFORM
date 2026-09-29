"""
Login Page – Streamlit
"""
import streamlit as st
import sys
import os

# Path setup
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(FRONTEND_DIR))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.auth.auth import login, ROLE_PERMISSIONS
from backend.security.audit_logger import log_event


def show_login_page():
    """Shfaq faqen e loginit."""

    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px;
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        margin-top: 80px;
    }
    .login-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
        text-align: center;
        margin-bottom: 8px;
    }
    .login-sub {
        color: #8b949e;
        text-align: center;
        font-size: 0.85rem;
        margin-bottom: 24px;
    }
    .role-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 2px;
    }
    .badge-admin { background: #da363340; color: #ff7b72; border: 1px solid #da3633; }
    .badge-analyst { background: #1f6feb40; color: #58a6ff; border: 1px solid #1f6feb; }
    .badge-viewer { background: #3fb95040; color: #3fb950; border: 1px solid #3fb950; }
    </style>
    """, unsafe_allow_html=True)

    # Login form
    st.markdown('<div class="login-title">🔐 OLAP BI Platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-sub">Siguri e Informacionit · Sistem Multi-Agent</div>', unsafe_allow_html=True)

    st.divider()

    # Demo accounts info
    with st.expander("👥 Llogaritë Demo"):
        cols = st.columns(3)
        with cols[0]:
            st.markdown('<span class="role-badge badge-admin">ADMIN</span>', unsafe_allow_html=True)
            st.code("admin\nadmin123")
        with cols[1]:
            st.markdown('<span class="role-badge badge-analyst">ANALYST</span>', unsafe_allow_html=True)
            st.code("analyst1\nanalyst123")
        with cols[2]:
            st.markdown('<span class="role-badge badge-viewer">VIEWER</span>', unsafe_allow_html=True)
            st.code("viewer1\nviewer123")

    st.markdown("**👤 Hyr në sistem**")

    username = st.text_input("Përdoruesi", placeholder="Shkruaj username...")
    password = st.text_input("Fjalëkalimi", type="password", placeholder="Shkruaj fjalëkalimin...")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔑 Hyr", use_container_width=True, type="primary"):
            if not username or not password:
                st.error("Plotëso të gjitha fushat!")
            else:
                result = login(username, password)
                if result["success"]:
                    from backend.auth.auth import is_2fa_enabled
                    if is_2fa_enabled(username):
                        # Kalo te 2FA
                        st.session_state.pending_2fa_username = username
                        log_event(username, "LOGIN", "Login i suksesshëm — duke pritur 2FA", success=True)
                        st.info("📱 Kodi 2FA po dërgohet në email...")
                        st.rerun()
                    else:
                        st.session_state.authenticated = True
                        st.session_state.username = result["username"]
                        st.session_state.role = result["role"]
                        st.session_state.full_name = result["full_name"]
                        st.session_state.permissions = result["permissions"]
                        st.session_state.token = result["token"]
                        log_event(username=username, event_type="LOGIN",
                            details=f"Login i suksesshëm — Role: {result['role']}", success=True)
                        st.success(f"Mirë se erdhe, {result['full_name']}! 🎉")
                        st.rerun()
                else:
                    log_event(username=username, event_type="LOGIN",
                        details=f"Login i dështuar: {result['error']}",
                        success=False, risk_level="HIGH")
                    st.error(result["error"])

    # Buton regjistrimi u hoq — vetëm admin mund të krijojë users nga brenda sistemit
    st.markdown("---")
    if st.button("🔓 Harrova Fjalëkalimin", use_container_width=True):
        st.session_state.show_forgot = True
        st.session_state.reset_step = 1
        st.rerun()


def show_register_page():
    """Faqja e regjistrimit — kërkon autentifikim admin."""
    if not st.session_state.get("authenticated") or st.session_state.get("role") != "admin":
        st.error("⛔ Akses i ndaluar! Vetëm administratorët mund të krijojnë llogari!")
        if st.button("← Kthehu te Login"):
            st.session_state.show_register = False
            st.rerun()
        return
    st.markdown("### 📝 Krijo Llogari të Re")
    st.info("✅ Vetëm administratorët mund të krijojnë llogari të reja!")

    from backend.auth.auth import register

    full_name = st.text_input("Emri i plotë")
    username = st.text_input("Username")
    password = st.text_input("Fjalëkalimi", type="password")
    role = st.selectbox("Role", ["viewer", "analyst", "admin"])

    st.markdown(f"**Permissions për '{role}':**")
    perms = ROLE_PERMISSIONS[role]
    for perm, value in perms.items():
        if perm != "description":
            icon = "✅" if value else "❌"
            st.markdown(f"{icon} {perm}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Krijo", type="primary"):
            result = register(username, password, role, full_name)
            if result["success"]:
                st.success(result["message"])
                st.session_state.show_register = False
            else:
                st.error(result["error"])
    with col2:
        if st.button("❌ Anulo"):
            st.session_state.show_register = False
            st.rerun()


def show_user_info():
    """Shfaq info të userit të loguar në sidebar."""
    role = st.session_state.get("role", "")
    username = st.session_state.get("username", "")
    full_name = st.session_state.get("full_name", "")

    badge_colors = {
        "admin": "badge-admin",
        "analyst": "badge-analyst",
        "viewer": "badge-viewer"
    }
    badge_class = badge_colors.get(role, "badge-viewer")

    st.markdown(f"""
    <div style="padding: 8px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 8px;">
        <div style="font-weight: 600; color: #fff;">👤 {full_name}</div>
        <div style="color: #8b949e; font-size: 0.8rem;">@{username}</div>
        <span class="role-badge {badge_class}">{role.upper()}</span>
    </div>
    """, unsafe_allow_html=True)

    # Admin: krijo user të ri
    if role == "admin":
        if st.button("➕ Krijo User të Ri", use_container_width=True):
            st.session_state.show_create_user = not st.session_state.get("show_create_user", False)
            st.rerun()

        if st.session_state.get("show_create_user"):
            st.markdown("---")
            st.markdown("**👤 Krijo User të Ri**")
            from backend.auth.auth import register
            new_full = st.text_input("Emri i plotë", key="new_full")
            new_user = st.text_input("Username", key="new_user")
            new_email = st.text_input("Email", key="new_email", placeholder="example@gmail.com")
            new_pass = st.text_input("Fjalëkalimi", type="password", key="new_pass")
            new_role = st.selectbox("Role", ["viewer", "analyst", "admin"], key="new_role")
            if st.button("✅ Krijo", key="create_user_btn"):
                from backend.auth.auth import register_with_email
                from backend.security.email_service import send_welcome_email
                result = register_with_email(new_user, new_pass, new_role, new_full, new_email)
                if result["success"]:
                    send_welcome_email(new_email, new_user, new_role)
                if result["success"]:
                    st.success(result["message"])
                    st.session_state.show_create_user = False
                    st.rerun()
                else:
                    st.error(result["error"])

    if st.button("🚪 Dil", use_container_width=True):
        from backend.security.audit_logger import log_event
        log_event(username, "LOGOUT", "Logout i suksesshëm")
        for key in ["authenticated", "username", "role", "full_name", "permissions", "token"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def show_user_management():
    """Panel i menaxhimit të users — vetëm për admin."""
    st.markdown("## 👥 Menaxhimi i Përdoruesve")
    st.caption("Lista e të gjithë përdoruesve dhe permissions e tyre")

    from backend.auth.auth import get_all_users, delete_user, ROLE_PERMISSIONS

    users = get_all_users()

    if not users:
        st.info("Nuk ka përdorues të regjistruar.")
        return

    # Statistika
    col1, col2, col3 = st.columns(3)
    admins = [u for u in users if u["role"] == "admin"]
    analysts = [u for u in users if u["role"] == "analyst"]
    viewers = [u for u in users if u["role"] == "viewer"]
    col1.metric("👑 Admin", len(admins))
    col2.metric("📊 Analyst", len(analysts))
    col3.metric("👁️ Viewer", len(viewers))

    st.divider()

    # Lista e users me permissions
    for user in users:
        role = user["role"]
        perms = ROLE_PERMISSIONS[role]

        badge_colors = {"admin": "🔴", "analyst": "🔵", "viewer": "🟢"}
        icon = badge_colors.get(role, "⚪")

        with st.expander(f"{icon} {user['full_name']} (@{user['username']}) — {role.upper()}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**ℹ️ Informacion**")
                st.write(f"👤 Username: ")
                st.write(f"📛 Emri: {user['full_name']}")
                st.write(f"🎭 Role: ")
                st.write(f"📅 Krijuar: {user['created_at'][:10]}")

            with col2:
                st.markdown("**🔐 Permissions**")
                perm_labels = {
                    "can_query": "🔍 Mund të bëjë query",
                    "can_view_audit": "📋 Sheh Audit Log",
                    "can_manage_users": "👥 Menaxhon users",
                    "can_export": "⬇️ Eksporton të dhëna",
                    "can_view_all_data": "📊 Sheh të gjitha të dhënat",
                }
                for perm_key, perm_label in perm_labels.items():
                    if perm_key in perms and perm_key != "description":
                        val = perms[perm_key]
                        icon_p = "✅" if val else "❌"
                        st.write(f"{icon_p} {perm_label}")

            # Fshi user (nuk mund të fshish veten ose admin kryesor)
            current_user = st.session_state.get("username", "")
            if user["username"] != "admin" and user["username"] != current_user:
                if st.button(f"🗑️ Fshi @{user['username']}", key=f"del_{user['username']}"):
                    result = delete_user(user["username"])
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["error"])
            else:
                st.caption("⚠️ Ky user nuk mund të fshihet")


def show_user_management():
    """Panel i menaxhimit të users — vetëm për admin."""
    st.markdown("## 👥 Menaxhimi i Përdoruesve")
    st.caption("Lista e të gjithë përdoruesve dhe permissions e tyre")

    from backend.auth.auth import get_all_users, delete_user, ROLE_PERMISSIONS

    users = get_all_users()

    if not users:
        st.info("Nuk ka përdorues të regjistruar.")
        return

    # Statistika
    col1, col2, col3 = st.columns(3)
    admins = [u for u in users if u["role"] == "admin"]
    analysts = [u for u in users if u["role"] == "analyst"]
    viewers = [u for u in users if u["role"] == "viewer"]
    col1.metric("👑 Admin", len(admins))
    col2.metric("📊 Analyst", len(analysts))
    col3.metric("👁️ Viewer", len(viewers))

    st.divider()

    perm_labels = {
        "can_query": "🔍 Mund të bëjë query",
        "can_view_audit": "📋 Sheh Audit Log",
        "can_manage_users": "👥 Menaxhon users",
        "can_export": "⬇️ Eksporton të dhëna",
        "can_view_all_data": "📊 Sheh të gjitha të dhënat",
    }

    badge_colors = {"admin": "🔴", "analyst": "🔵", "viewer": "🟢"}
    current_user = st.session_state.get("username", "")

    for user in users:
        role = user["role"]
        perms = ROLE_PERMISSIONS[role]
        icon = badge_colors.get(role, "⚪")
        uname = user["username"]
        fname = user["full_name"]
        created = user["created_at"][:10]

        with st.expander(f"{icon} {fname} (@{uname}) — {role.upper()}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**ℹ️ Informacion**")
                st.write(f"👤 Username: `{uname}`")
                st.write(f"📛 Emri: {fname}")
                st.write(f"🎭 Role: `{role}`")
                st.write(f"📅 Krijuar: {created}")

            with col2:
                st.markdown("**🔐 Permissions**")
                for perm_key, perm_label in perm_labels.items():
                    if perm_key in perms:
                        val = perms[perm_key]
                        icon_p = "✅" if val else "❌"
                        st.write(f"{icon_p} {perm_label}")

            if uname != "admin" and uname != current_user:
                if st.button(f"🗑️ Fshi @{uname}", key=f"del_{uname}"):
                    result = delete_user(uname)
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["error"])
            else:
                st.caption("⚠️ Ky user nuk mund të fshihet")
