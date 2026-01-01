from sqlalchemy.orm import Session
from app.models.models import Watermark
from app.services.watermark.lsb.watermark_lsb_extractor import extract_image_watermark


def verify_image_watermark(
    image_bytes: bytes,
    watermark_id: str,
    db: Session
) -> dict:

    extracted_signature = extract_image_watermark(image_bytes)

    if not extracted_signature:
        return {
            "verified": False,
            "reason": "no watermark found"
        }

    record = db.query(Watermark).filter(
        Watermark.id == watermark_id,
        Watermark.status == "active"
    ).first()

    if not record:
        return {
            "verified": False,
            "reason": "watermark id not found"
        }

    if extracted_signature != record.signature_hash[:32]:
        return {
            "verified": False,
            "reason": "watermark signature mismatch"
        }

    return {
        "verified": True,
        "owner_id": record.owner_id,
        "content_type": record.content_type,
        "mime_type": record.mime_type,
        "issued_at": record.created_at,
        "algorithm_version": record.algorithm_version
    }
