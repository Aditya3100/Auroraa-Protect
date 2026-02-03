# app/services/watermark/document/doc_crypto.py

import os
import json
import hmac
import hashlib
import base64


SECRET = os.environ.get("AURORAA_WATERMARK_SECRET")

if not SECRET:
    raise RuntimeError("Missing AURORAA_WATERMARK_SECRET")

SECRET = SECRET.encode()


# --------------------------------
# Payload Generator
# --------------------------------

def generate_payload(watermark):

    data = {
        "wid": watermark.id,
        "uid": watermark.owner_id,
        "alg": watermark.algorithm_version,
        "ts": int(__import__("time").time())
    }

    msg = json.dumps(data, sort_keys=True).encode()

    sig = hmac.new(
        SECRET,
        msg,
        hashlib.sha256
    ).hexdigest()

    data["sig"] = sig

    raw = json.dumps(data).encode()

    return base64.b64encode(raw).decode()


# --------------------------------
# Payload Decoder
# --------------------------------

def decode_payload(encoded: str):

    try:
        raw = base64.b64decode(encoded)
        return json.loads(raw)

    except Exception:
        return None


# --------------------------------
# Signature Verification
# --------------------------------

def verify_signature(payload: dict) -> bool:

    try:
        # sig = payload.pop("sig", None)
        sig = payload.get("sig")
        payload = payload.copy()
        payload.pop("sig", None)


        if not sig:
            return False

        msg = json.dumps(payload, sort_keys=True).encode()

        expected = hmac.new(
            SECRET,
            msg,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(sig, expected)

    except Exception:
        return False
