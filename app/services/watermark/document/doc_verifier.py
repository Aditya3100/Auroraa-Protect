from sqlalchemy.orm import Session

from .doc_crypto import decode_payload, verify_signature
from app.models.models import Watermark


VERIFY_THRESHOLD = 0.7


def verify(
    extracted_bits=None,
    extracted_text=None,
    owner_id: str = None,
    algorithm_version: str = None,
    db: Session = None
):
    """
    Route-compatible Phase-1 verifier
    Accepts extracted_bits OR extracted_text
    """

    # ---------------------------
    # Normalize Input
    # ---------------------------

    if extracted_text is None and extracted_bits is not None:

        # Legacy: bits → string
        try:
            if isinstance(extracted_bits, str):
                extracted_text = extracted_bits
            else:
                extracted_text = "".join(map(str, extracted_bits))
        except Exception:
            extracted_text = None


    if not extracted_text:
        return False, 0.0, None


    # ---------------------------
    # Decode Payload
    # ---------------------------

    payload = decode_payload(extracted_text)

    if not payload:
        return False, 0.0, None


    # ---------------------------
    # DB Binding
    # ---------------------------

    if db:

        wm = db.query(Watermark).filter(
            Watermark.id == payload.get("wid"),
            Watermark.owner_id == owner_id,
            Watermark.status == "active"
        ).first()

        if not wm:
            return False, 0.0, None


    # ---------------------------
    # Ownership
    # ---------------------------

    if payload.get("uid") != owner_id:
        return False, 0.0, None


    if payload.get("alg") != algorithm_version:
        return False, 0.0, None


    # ---------------------------
    # Crypto
    # ---------------------------

    if not verify_signature(payload):
        return False, 0.0, None


    # ---------------------------
    # Confidence (Phase-1)
    # ---------------------------

    length = len(extracted_text)

    confidence = min(1.0, length / 256)


    verified = confidence >= VERIFY_THRESHOLD


    return verified, confidence, payload.get("wid")
