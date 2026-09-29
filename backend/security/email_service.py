"""
Email Service Module
- Dërgon kode verifikimi me Gmail
- Reset password codes
- 2FA codes
"""
import os
import smtplib

# Load .env file manually
def _load_env():
    env_paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        ".env"
    ]
    for path in env_paths:
        path = os.path.abspath(path)
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        os.environ.setdefault(key.strip(), val.strip())
            break

_load_env()
import random
import string
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
def _get_gmail():
    return os.getenv("GMAIL_ADDRESS", ""), os.getenv("GMAIL_APP_PASSWORD", "")

# Ruaj kodet aktive në memorie {email: {code, expires, type}}
_active_codes = {}


def _generate_code(length: int = 6) -> str:
    """Gjenero kod numerik 6-shifror."""
    return "".join(random.choices(string.digits, k=length))


def _send_email(to_email: str, subject: str, html_body: str) -> dict:
    """Dërgo email me Gmail SMTP."""
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD = _get_gmail()
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return {
            "success": False,
            "error": "Email nuk është konfiguruar! Shto GMAIL_ADDRESS dhe GMAIL_APP_PASSWORD në .env"
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"OLAP BI Platform <{GMAIL_ADDRESS}>"
        msg["To"] = to_email

        part = MIMEText(html_body, "html")
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD.replace(" ", ""))
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        return {"success": True, "message": f"Email u dërgua te {to_email}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Gmail authentication failed! Kontrollo App Password-in."
        }
    except Exception as e:
        return {"success": False, "error": f"Email error: {str(e)}"}


def send_reset_code(to_email: str, username: str) -> dict:
    """Dërgo kod për reset të fjalëkalimit."""
    code = _generate_code(6)
    expires = int(time.time()) + 600  # 10 minuta

    _active_codes[to_email] = {
        "code": code,
        "expires": expires,
        "type": "reset",
        "username": username
    }

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="background: #1a1a2e; padding: 30px; border-radius: 10px; text-align: center;">
            <h2 style="color: #58a6ff;">🔐 OLAP BI Platform</h2>
            <h3 style="color: #fff;">Reset Fjalëkalimit</h3>
        </div>
        <div style="padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px;">
            <p>Përshëndetje <strong>{username}</strong>!</p>
            <p>Kodi juaj i resetimit të fjalëkalimit është:</p>
            <div style="text-align: center; margin: 30px 0;">
                <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                             background: #1a1a2e; color: #58a6ff; padding: 15px 25px;
                             border-radius: 8px;">{code}</span>
            </div>
            <p style="color: #666;">⏰ Ky kod skadon pas <strong>10 minutave</strong>.</p>
            <p style="color: #666;">Nëse nuk e kërkuat ju, injoroni këtë email.</p>
            <hr>
            <p style="font-size: 12px; color: #999;">OLAP BI Platform — Siguri e Informacionit</p>
        </div>
    </div>
    """

    return _send_email(to_email, "🔐 Kodi i Resetimit të Fjalëkalimit", html)


def send_2fa_code(to_email: str, username: str) -> dict:
    """Dërgo kod 2FA pas login."""
    code = _generate_code(6)
    expires = int(time.time()) + 300  # 5 minuta

    _active_codes[f"2fa_{to_email}"] = {
        "code": code,
        "expires": expires,
        "type": "2fa",
        "username": username
    }

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="background: #1a1a2e; padding: 30px; border-radius: 10px; text-align: center;">
            <h2 style="color: #58a6ff;">🔐 OLAP BI Platform</h2>
            <h3 style="color: #fff;">Verifikimi me Dy Hapa (2FA)</h3>
        </div>
        <div style="padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px;">
            <p>Përshëndetje <strong>{username}</strong>!</p>
            <p>Kodi juaj i verifikimit është:</p>
            <div style="text-align: center; margin: 30px 0;">
                <span style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                             background: #1a1a2e; color: #3fb950; padding: 15px 25px;
                             border-radius: 8px;">{code}</span>
            </div>
            <p style="color: #666;">⏰ Ky kod skadon pas <strong>5 minutave</strong>.</p>
            <p style="color: #red;">🚨 Nëse nuk jeni ju, ndryshoni fjalëkalimin menjëherë!</p>
            <hr>
            <p style="font-size: 12px; color: #999;">OLAP BI Platform — Siguri e Informacionit</p>
        </div>
    </div>
    """

    return _send_email(to_email, "🔐 Kodi i Verifikimit 2FA", html)


def verify_code(email: str, code: str, code_type: str = "reset") -> dict:
    """Verifiko kodin e dërguar."""
    key = f"2fa_{email}" if code_type == "2fa" else email

    if key not in _active_codes:
        return {"success": False, "error": "Kodi nuk ekziston ose ka skaduar!"}

    stored = _active_codes[key]

    if int(time.time()) > stored["expires"]:
        del _active_codes[key]
        return {"success": False, "error": "Kodi ka skaduar! Kërko kod të ri."}

    if stored["code"] != code.strip():
        return {"success": False, "error": "Kodi është i gabuar!"}

    del _active_codes[key]
    return {"success": True, "username": stored.get("username", "")}


def send_welcome_email(to_email: str, username: str, role: str) -> dict:
    """Dërgo email mirëseardhjeje kur krijohet llogaria."""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="background: #1a1a2e; padding: 30px; border-radius: 10px; text-align: center;">
            <h2 style="color: #58a6ff;">🎉 Mirë se erdhe!</h2>
            <h3 style="color: #fff;">OLAP BI Platform</h3>
        </div>
        <div style="padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px;">
            <p>Përshëndetje <strong>{username}</strong>!</p>
            <p>Llogaria juaj u krijua me sukses.</p>
            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background: #f0f0f0;">
                    <td style="padding: 10px; font-weight: bold;">👤 Username:</td>
                    <td style="padding: 10px;">{username}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; font-weight: bold;">🎭 Role:</td>
                    <td style="padding: 10px;">{role.upper()}</td>
                </tr>
                <tr style="background: #f0f0f0;">
                    <td style="padding: 10px; font-weight: bold;">📧 Email:</td>
                    <td style="padding: 10px;">{to_email}</td>
                </tr>
            </table>
            <p style="color: #666;">Mund të hyni në sistem me username dhe fjalëkalimin tuaj.</p>
            <hr>
            <p style="font-size: 12px; color: #999;">OLAP BI Platform — Siguri e Informacionit</p>
        </div>
    </div>
    """
    return _send_email(to_email, "🎉 Mirë se erdhe në OLAP BI Platform!", html)
