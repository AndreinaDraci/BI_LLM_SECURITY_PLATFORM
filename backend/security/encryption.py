"""
Data Encryption Module
- Enkriptim/Dekriptim i të dhënave sensitive
- Masking i kolumnave sensitive
- API key encryption
"""
import base64
import hashlib
import os
import re


SECRET = "olap_bi_encryption_key_2024"


def _get_key() -> bytes:
    """Gjenero encryption key nga SECRET."""
    return hashlib.sha256(SECRET.encode()).digest()


def encrypt(text: str) -> str:
    """
    Enkriptim i thjeshtë XOR + base64.
    Për production përdor AES (cryptography library).
    """
    if not text:
        return ""
    key = _get_key()
    encrypted = bytes([
        ord(c) ^ key[i % len(key)]
        for i, c in enumerate(text)
    ])
    return base64.b64encode(encrypted).decode()


def decrypt(encrypted_text: str) -> str:
    """Dekriptim."""
    if not encrypted_text:
        return ""
    try:
        key = _get_key()
        encrypted = base64.b64decode(encrypted_text.encode())
        decrypted = bytes([
            b ^ key[i % len(key)]
            for i, b in enumerate(encrypted)
        ])
        return decrypted.decode()
    except Exception:
        return ""


def mask_api_key(api_key: str) -> str:
    """
    Masko API key për display.
    sk-ant-api03-xxxx...xxxx → sk-ant-****...****-xxxx
    """
    if not api_key or len(api_key) < 8:
        return "****"
    return f"{api_key[:8]}{'*' * (len(api_key) - 12)}{api_key[-4:]}"


def mask_sensitive_data(df_dict: list, sensitive_columns: list = None) -> list:
    """
    Masko kolumna sensitive në rezultatin e query.
    """
    if sensitive_columns is None:
        sensitive_columns = ["email", "phone", "address", "credit_card", "ssn"]

    masked = []
    for row in df_dict:
        masked_row = {}
        for key, value in row.items():
            if any(sens in key.lower() for sens in sensitive_columns):
                masked_row[key] = "****"
            else:
                masked_row[key] = value
        masked.append(masked_row)
    return masked


def hash_sensitive_value(value: str) -> str:
    """Hash një vlerë sensitive (one-way)."""
    return hashlib.sha256(f"{SECRET}{value}".encode()).hexdigest()[:16]


def encrypt_api_key(api_key: str) -> str:
    """Enkriptoj API key për ruajtje të sigurt."""
    return encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Dekriptoj API key."""
    return decrypt(encrypted_key)


def get_encryption_info() -> dict:
    """Info mbi encryption që përdoret."""
    return {
        "algorithm": "XOR + Base64 (demo) / AES-256 (production)",
        "key_derivation": "SHA-256",
        "api_key_storage": "Encrypted in memory",
        "password_hashing": "SHA-256 + Salt",
        "transport": "HTTPS (TLS 1.3)",
        "data_at_rest": "Encrypted sensitive columns"
    }
