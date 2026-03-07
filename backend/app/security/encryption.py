"""
Nova AI Life Assistant — AES-256-GCM Encryption
"""
import base64
import os
from Crypto.Cipher import AES
from app.config import get_settings


def _get_key() -> bytes:
    """Get the 32-byte AES key from settings (stored as 64-char hex)."""
    key_hex = get_settings().AES_KEY
    if not key_hex or len(key_hex) < 64:
        raise ValueError(
            "AES_KEY must be a 64-character hex string (32 bytes). "
            "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return bytes.fromhex(key_hex)


def encrypt(plaintext: str) -> str:
    """
    Encrypt plaintext using AES-256-GCM.
    Returns base64-encoded string containing: nonce (12B) + ciphertext + tag (16B).
    """
    if not plaintext:
        return ""
    key = _get_key()
    nonce = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    # Pack: nonce + ciphertext + tag
    packed = nonce + ciphertext + tag
    return base64.b64encode(packed).decode("utf-8")


def decrypt(encrypted: str) -> str:
    """
    Decrypt a base64-encoded AES-256-GCM ciphertext.
    """
    if not encrypted:
        return ""
    key = _get_key()
    packed = base64.b64decode(encrypted)
    nonce = packed[:12]
    tag = packed[-16:]
    ciphertext = packed[12:-16]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext.decode("utf-8")


def mask_identifier(value: str, visible_chars: int = 2) -> str:
    """
    Mask a sensitive identifier.
    Example: 'ajsal@upi' → 'aj***@upi'
    """
    if not value:
        return ""
    if "@" in value:
        local, domain = value.rsplit("@", 1)
        masked_local = local[:visible_chars] + "***" if len(local) > visible_chars else local
        return f"{masked_local}@{domain}"
    if len(value) <= visible_chars * 2:
        return value
    return value[:visible_chars] + "***" + value[-visible_chars:]
