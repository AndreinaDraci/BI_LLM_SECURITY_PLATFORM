"""
Password Management Pages:
- Change Password
- Forgot Password (me kod email)
- 2FA Setup & Verification
"""
import streamlit as st
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.auth.auth import (change_password, reset_password,
    get_email_by_username, get_username_by_email, toggle_2fa, is_2fa_enabled)
from backend.security.email_service import send_reset_code, send_2fa_code, verify_code
from backend.security.audit_logger import log_event


def show_change_password():
    """Faqja e ndryshimit të fjalëkalimit."""
    st.markdown("## 🔑 Ndrysho Fjalëkalimin")
    username = st.session_state.get("username", "")

    with st.form("change_pass_form"):
        old_pass = st.text_input("🔒 Fjalëkalimi i vjetër", type="password")
        new_pass = st.text_input("🔑 Fjalëkalimi i ri", type="password")
        confirm_pass = st.text_input("✅ Konfirmo fjalëkalimin e ri", type="password")

        st.markdown("**Kriteret:**")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("✅ Min 6 karaktere" if len(new_pass) >= 6 else "❌ Min 6 karaktere")
            st.markdown("✅ I ndryshëm" if new_pass != old_pass and new_pass else "❌ I ndryshëm")
        with col2:
            st.markdown("✅ Konfirmimi OK" if new_pass == confirm_pass and new_pass else "❌ Konfirmimi OK")

        submitted = st.form_submit_button("🔄 Ndrysho", use_container_width=True)
        if submitted:
            if not old_pass or not new_pass or not confirm_pass:
                st.error("Plotëso të gjitha fushat!")
            elif new_pass != confirm_pass:
                st.error("Fjalëkalimet nuk përputhen!")
            else:
                result = change_password(username, old_pass, new_pass)
                if result["success"]:
                    log_event(username, "PASSWORD_CHANGE", "Fjalëkalimi u ndryshua", success=True)
                    st.success("✅ " + result["message"])
                    st.balloons()
                else:
                    log_event(username, "PASSWORD_CHANGE", result["error"], success=False, risk_level="HIGH")
                    st.error("❌ " + result["error"])

    # 2FA Settings
    st.divider()
    st.markdown("## 📱 Verifikimi me Dy Hapa (2FA)")
    email = get_email_by_username(username)
    is_enabled = is_2fa_enabled(username)

    if email:
        st.info(f"📧 Kodet dërgohen te: **{email}**")
        if not is_enabled:
            if st.button("✅ Aktivizo 2FA", type="primary", use_container_width=True):
                result = toggle_2fa(username, True)
                st.success(result["message"])
                log_event(username, "2FA_ENABLED", "2FA u aktivizua", success=True)
                st.rerun()
        else:
            st.success("🟢 2FA është aktiv!")
            if st.button("❌ Çaktivizo 2FA", use_container_width=True):
                result = toggle_2fa(username, False)
                st.warning(result["message"])
                log_event(username, "2FA_DISABLED", "2FA u çaktivizua", success=True, risk_level="MEDIUM")
                st.rerun()
    else:
        st.warning("⚠️ Llogaria juaj nuk ka email. Kontaktoni administratorin.")


def show_forgot_password():
    """Faqja e 'Harrova Fjalëkalimin' — 3 hapa."""
    st.markdown("## 🔓 Rivendos Fjalëkalimin")
    step = st.session_state.get("reset_step", 1)

    # Progress bar
    st.progress(step / 3)
    st.caption(f"Hapi {step} nga 3")

    # HAPI 1: Username + Email
    if step == 1:
        st.markdown("### 👤 Hapi 1 — Verifiko Identitetin")
        st.info("Shkruaj username-in dhe email-in e regjistruar në llogari.")
        with st.form("forgot_form"):
            username_input = st.text_input("👤 Username", placeholder="Shkruaj username-in tënd")
            email_input = st.text_input("📧 Email", placeholder="example@gmail.com")
            submitted = st.form_submit_button("📨 Dërgo Kodin", use_container_width=True)
            if submitted:
                if not username_input or not email_input:
                    st.error("Plotëso të dyja fushat!")
                elif "@" not in email_input:
                    st.error("Shkruaj email të vlefshëm!")
                else:
                    # Verifiko që username dhe email përputhen
                    real_email = get_email_by_username(username_input)
                    if not real_email:
                        st.error("❌ Ky username nuk ekziston!")
                    elif real_email.lower() != email_input.lower().strip():
                        st.error("❌ Email nuk përputhet me këtë username!")
                        log_event(username_input, "PASSWORD_RESET_FAILED", 
                            "Email nuk përputhet", success=False, risk_level="HIGH")
                    else:
                        with st.spinner("Duke dërguar kodin..."):
                            result = send_reset_code(real_email, username_input)
                        if result["success"]:
                            st.session_state.reset_email = real_email
                            st.session_state.reset_username = username_input
                            st.session_state.reset_step = 2
                            log_event(username_input, "PASSWORD_RESET_REQUEST", 
                                f"Kod dërguar te {real_email}")
                            st.success(f"✅ Kodi u dërgua te {real_email}!")
                            st.rerun()
                        else:
                            st.error("❌ " + result["error"])

        if st.button("← Kthehu te Login"):
            st.session_state.show_forgot = False
            st.session_state.reset_step = 1
            st.rerun()

    # HAPI 2: Kod
    elif step == 2:
        email = st.session_state.get("reset_email", "")
        username = st.session_state.get("reset_username", "")
        st.info(f"📧 Kodi u dërgua te: **{email}**")
        st.markdown("### 🔢 Hapi 2 — Fut Kodin")

        with st.form("code_form"):
            code = st.text_input("Kodi 6-shifror", placeholder="123456", max_chars=6)
            submitted = st.form_submit_button("✅ Verifiko", use_container_width=True)
            if submitted:
                result = verify_code(email, code, "reset")
                if result["success"]:
                    st.session_state.reset_step = 3
                    st.rerun()
                else:
                    st.error("❌ " + result["error"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📨 Ridërgo Kodin"):
                send_reset_code(email, username)
                st.success("Kodi u ridërgua!")
        with col2:
            if st.button("← Kthehu"):
                st.session_state.reset_step = 1
                st.rerun()

    # HAPI 3: Fjalëkalim i ri
    elif step == 3:
        username = st.session_state.get("reset_username", "")
        st.success("✅ Identiteti u verifikua!")
        st.markdown("### 🔑 Hapi 3 — Fjalëkalim i Ri")

        with st.form("new_pass_form"):
            new_pass = st.text_input("Fjalëkalimi i ri", type="password")
            confirm_pass = st.text_input("Konfirmo fjalëkalimin", type="password")
            submitted = st.form_submit_button("💾 Ruaj", use_container_width=True)
            if submitted:
                if new_pass != confirm_pass:
                    st.error("Fjalëkalimet nuk përputhen!")
                else:
                    result = reset_password(username, new_pass)
                    if result["success"]:
                        log_event(username, "PASSWORD_RESET", "Fjalëkalimi u resetua", success=True)
                        st.success("✅ " + result["message"])
                        st.balloons()
                        st.session_state.reset_step = 1
                        st.session_state.show_forgot = False
                        st.rerun()
                    else:
                        st.error("❌ " + result["error"])


def show_2fa_verification():
    """Verifikimi 2FA pas login."""
    st.markdown("## 📱 Verifikimi me Dy Hapa (2FA)")
    username = st.session_state.get("pending_2fa_username", "")
    email = get_email_by_username(username)

    if not email:
        st.error("Email nuk u gjet!")
        return

    if not st.session_state.get("2fa_code_sent"):
        with st.spinner("Duke dërguar kodin..."):
            result = send_2fa_code(email, username)
        if result["success"]:
            st.session_state["2fa_code_sent"] = True
        else:
            st.error("❌ " + result["error"])
            return

    st.info(f"📧 Kodi u dërgua te: **{email}**")
    st.caption("⏰ Kodi skadon pas 5 minutave")

    with st.form("2fa_form"):
        code = st.text_input("🔢 Kodi 6-shifror", placeholder="123456", max_chars=6)
        submitted = st.form_submit_button("✅ Hyr", use_container_width=True)
        if submitted:
            result = verify_code(email, code, "2fa")
            if result["success"]:
                from backend.auth.auth import _load_users, _generate_token, ROLE_PERMISSIONS
                users = _load_users()
                user = users.get(username, {})
                token = _generate_token(username, user["role"])
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = user["role"]
                st.session_state.full_name = user["full_name"]
                st.session_state.permissions = ROLE_PERMISSIONS[user["role"]]
                st.session_state.token = token
                st.session_state.pop("pending_2fa_username", None)
                st.session_state.pop("2fa_code_sent", None)
                log_event(username, "2FA_SUCCESS", "2FA verifikuar me sukses", success=True)
                st.rerun()
            else:
                log_event(username, "2FA_FAILED", result["error"], success=False, risk_level="HIGH")
                st.error("❌ " + result["error"])

    if st.button("📨 Ridërgo Kodin"):
        st.session_state["2fa_code_sent"] = False
        st.rerun()
