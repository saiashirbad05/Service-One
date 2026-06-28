import hmac
import hashlib
import time
import os
import urllib.parse
from typing import Dict, Any

from config import settings

SECRET_SIGNING_KEY = settings.JWT_SECRET_KEY

def generate_signed_url(filename: str, expires_in_seconds: int = 900, base_url: str = "http://localhost:8000") -> str:
    """
    [BE-5] Secure GCS Storage with auto-expiring signed URLs.
    Generates a secure HTTPS link to a file that automatically expires after expires_in_seconds (default 15m).
    Utilizes HMAC-SHA256 signature validation matching professional cloud storage parameters.
    """
    expires = int(time.time()) + expires_in_seconds
    
    # Message format: "filename:expires"
    message = f"{filename}:{expires}".encode("utf-8")
    
    # Calculate HMAC-SHA256 signature
    signature = hmac.new(
        SECRET_SIGNING_KEY.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Return signed endpoint URL
    encoded_filename = urllib.parse.quote(filename)
    return f"{base_url.rstrip('/')}/api/secure-file/{encoded_filename}?expires={expires}&signature={signature}"

def verify_signed_url(filename: str, expires: int, signature: str) -> bool:
    """
    Verifies the signature and check if the URL has expired.
    Returns True if valid, False otherwise.
    """
    # 1. Check expiration
    if time.time() > expires:
        print(f"[SecureGCS] Verification failed: URL expired at {expires}, current {time.time()}")
        return False
        
    # 2. Recalculate signature
    message = f"{filename}:{expires}".encode("utf-8")
    expected_signature = hmac.new(
        SECRET_SIGNING_KEY.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # 3. Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)
