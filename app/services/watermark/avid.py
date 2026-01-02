import hmac
import hashlib

AURORAA_SECRET = b"server-secret-never-exposed"  # move to env in prod


def generate_awid(owner_id: str, algorithm_version: str = "v1") -> bytes:
    """
    Stable Auroraa Watermark Identity (AWID)
    Same owner_id + version => same watermark forever
    """
    msg = f"auroraa:{algorithm_version}:{owner_id}".encode()
    return hmac.new(AURORAA_SECRET, msg, hashlib.sha256).digest()
