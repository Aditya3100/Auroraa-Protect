import hmac
import hashlib

def generate_signature(asset_id: str, issued_at: str, secret_key: bytes) -> str:
    message = f"{asset_id}|{issued_at}".encode()
    return hmac.new(secret_key, message, hashlib.sha256).hexdigest()

def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()
