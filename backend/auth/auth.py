"""
Authentication Module
- Register/Login users
- JWT token generation & validation
- Password hashing with bcrypt
"""
import os
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime
from typing import Optional

# ── Skedar ku ruhen users (në vend të DB për thjeshtësi) ─────────────────────
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
SECRET_KEY = "olap_bi_secret_key_2024_secure"  # Në production përdor env variable

# ── Role permissions ──────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "admin": {
        "can_query": True,
        "can_view_audit": True,
        "can_manage_users": True,
        "can_export": True,
        "can_view_all_data": True,
        "description": "Akses i plotë në sistem"
    },
    "analyst": {
        "can_query": True,
        "can_view_audit": False,
        "can_manage_users": False,
        "can_export": True,
        "can_view_all_data": True,
        "description": "Mund të bëjë analiza dhe eksportojë"
    },
    "viewer": {
        "can_query": True,
        "can_view_audit": False,
        "can_manage_users": False,
        "can_export": False,
        "can_view_all_data": False,
        "description": "Vetëm shikues i rezultateve"
    }
}


def _load_users() -> dict:
    """Ngarko users nga skedar JSON."""
    if not os.path.exists(USERS_FILE):
        # Krijo users default
        default_users = {
            "admin": {
                "password_hash": _hash_password("admin123"),
                "role": "admin",
                "email": "admin@olap-platform.com",
                "created_at": datetime.now().isoformat(),
                "full_name": "Administrator",
                "2fa_enabled": False
            },
            "analyst1": {
                "password_hash": _hash_password("analyst123"),
                "role": "analyst",
                "email": "analyst1@olap-platform.com",
                "created_at": datetime.now().isoformat(),
                "full_name": "Ana Analyst",
                "2fa_enabled": False
            },
            "viewer1": {
                "password_hash": _hash_password("viewer123"),
                "role": "viewer",
                "email": "viewer1@olap-platform.com",
                "created_at": datetime.now().isoformat(),
                "full_name": "Viktor Viewer",
                "2fa_enabled": False
            }
        }
        _save_users(default_users)
        return default_users

    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(users: dict):
    """Ruaj users në skedar JSON."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    """Hash fjalëkalimin me SHA-256 + salt."""
    salt = "olap_bi_salt_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _generate_token(username: str, role: str) -> str:
    """Gjenero JWT token të thjeshtë."""
    payload = {
        "username": username,
        "role": role,
        "exp": int(time.time()) + 3600  # 1 orë
    }
    payload_b64 = base64.b64encode(
        json.dumps(payload).encode()
    ).decode()

    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{payload_b64}.{signature}"


def _verify_token(token: str) -> Optional[dict]:
    """Verifiko JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, signature = parts

        # Verifiko signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Dekodo payload
        payload = json.loads(base64.b64decode(payload_b64).decode())

        # Kontrollo expiration
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


def login(username: str, password: str) -> dict:
    """
    Login user.
    Returns: {"success": True, "token": "...", "role": "...", "full_name": "..."}
    """
    users = _load_users()

    if username not in users:
        return {"success": False, "error": "Përdoruesi nuk ekziston!"}

    user = users[username]
    if user["password_hash"] != _hash_password(password):
        return {"success": False, "error": "Fjalëkalimi është i gabuar!"}

    token = _generate_token(username, user["role"])

    return {
        "success": True,
        "token": token,
        "username": username,
        "role": user["role"],
        "full_name": user["full_name"],
        "permissions": ROLE_PERMISSIONS[user["role"]]
    }


def register(username: str, password: str, role: str, full_name: str) -> dict:
    """
    Regjistro user të ri (vetëm admin mund të bëjë).
    """
    users = _load_users()

    if username in users:
        return {"success": False, "error": "Përdoruesi ekziston tashmë!"}

    if role not in ROLE_PERMISSIONS:
        return {"success": False, "error": f"Role i pavlefshëm! Zgjidh: {list(ROLE_PERMISSIONS.keys())}"}

    if len(password) < 6:
        return {"success": False, "error": "Fjalëkalimi duhet të ketë të paktën 6 karaktere!"}

    users[username] = {
        "password_hash": _hash_password(password),
        "role": role,
        "created_at": datetime.now().isoformat(),
        "full_name": full_name
    }
    _save_users(users)

    return {"success": True, "message": f"Përdoruesi '{username}' u krijua me role '{role}'!"}


def verify_session(token: str) -> Optional[dict]:
    """Verifiko sesionin aktual."""
    return _verify_token(token)


def get_all_users() -> list:
    """Merr listën e të gjithë users (vetëm për admin)."""
    users = _load_users()
    return [
        {
            "username": u,
            "role": data["role"],
            "full_name": data["full_name"],
            "created_at": data["created_at"]
        }
        for u, data in users.items()
    ]


def delete_user(username: str) -> dict:
    """Fshi user (vetëm admin)."""
    users = _load_users()
    if username not in users:
        return {"success": False, "error": "Përdoruesi nuk ekziston!"}
    if username == "admin":
        return {"success": False, "error": "Nuk mund të fshish admin-in kryesor!"}
    del users[username]
    _save_users(users)
    return {"success": True, "message": f"Përdoruesi '{username}' u fshi!"}


def get_permissions(role: str) -> dict:
    """Merr permissions për një role."""
    return ROLE_PERMISSIONS.get(role, {})


def register_with_email(username: str, password: str, role: str, full_name: str, email: str) -> dict:
    """Regjistro user të ri me email."""
    users = _load_users()

    if username in users:
        return {"success": False, "error": "Përdoruesi ekziston tashmë!"}

    # Kontrollo nëse email ekziston
    for u, data in users.items():
        if data.get("email", "") == email:
            return {"success": False, "error": "Ky email është përdorur tashmë!"}

    if role not in ROLE_PERMISSIONS:
        return {"success": False, "error": f"Role i pavlefshëm!"}

    if len(password) < 6:
        return {"success": False, "error": "Fjalëkalimi duhet të ketë të paktën 6 karaktere!"}

    if "@" not in email:
        return {"success": False, "error": "Email i pavlefshëm!"}

    users[username] = {
        "password_hash": _hash_password(password),
        "role": role,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "full_name": full_name,
        "2fa_enabled": False
    }
    _save_users(users)
    return {"success": True, "message": f"Përdoruesi '{username}' u krijua!", "email": email}


def get_email_by_username(username: str) -> Optional[str]:
    """Merr email-in e një user."""
    users = _load_users()
    if username in users:
        return users[username].get("email", "")
    return None


def get_username_by_email(email: str) -> Optional[str]:
    """Merr username-in nga email."""
    users = _load_users()
    for username, data in users.items():
        if data.get("email", "") == email:
            return username
    return None


def change_password(username: str, old_password: str, new_password: str) -> dict:
    """Ndrysho fjalëkalimin me fjalëkalim të vjetër."""
    users = _load_users()

    if username not in users:
        return {"success": False, "error": "Përdoruesi nuk ekziston!"}

    if users[username]["password_hash"] != _hash_password(old_password):
        return {"success": False, "error": "Fjalëkalimi i vjetër është i gabuar!"}

    if len(new_password) < 6:
        return {"success": False, "error": "Fjalëkalimi i ri duhet të ketë të paktën 6 karaktere!"}

    if old_password == new_password:
        return {"success": False, "error": "Fjalëkalimi i ri duhet të jetë i ndryshëm!"}

    users[username]["password_hash"] = _hash_password(new_password)
    _save_users(users)
    return {"success": True, "message": "Fjalëkalimi u ndryshua me sukses!"}


def reset_password(username: str, new_password: str) -> dict:
    """Reset fjalëkalimin pas verifikimit të kodit."""
    users = _load_users()

    if username not in users:
        return {"success": False, "error": "Përdoruesi nuk ekziston!"}

    if len(new_password) < 6:
        return {"success": False, "error": "Fjalëkalimi duhet të ketë të paktën 6 karaktere!"}

    users[username]["password_hash"] = _hash_password(new_password)
    _save_users(users)
    return {"success": True, "message": "Fjalëkalimi u resetua me sukses!"}


def toggle_2fa(username: str, enabled: bool) -> dict:
    """Aktivizo/çaktivizo 2FA për user."""
    users = _load_users()
    if username not in users:
        return {"success": False, "error": "Përdoruesi nuk ekziston!"}
    users[username]["2fa_enabled"] = enabled
    _save_users(users)
    status = "aktivizuar" if enabled else "çaktivizuar"
    return {"success": True, "message": f"2FA u {status}!"}


def is_2fa_enabled(username: str) -> bool:
    """Kontrollo nëse 2FA është aktiv."""
    users = _load_users()
    if username in users:
        return users[username].get("2fa_enabled", False)
    return False
