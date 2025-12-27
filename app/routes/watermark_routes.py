from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.models import Watermark
from app.schemas.watermark_schemas import WatermarkCreate, WatermarkVerify
from app.database.database import get_db

router = APIRouter()


@router.post("/watermark/store")
def store_watermark(data: WatermarkCreate, db: Session = Depends(get_db)):
    record = Watermark(**data.dict())
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "stored", "id": record.id}

@router.post("/watermark/verify")
def verify_watermark(data: WatermarkVerify, db: Session = Depends(get_db)):
    record = db.query(Watermark).filter(
        Watermark.asset_id == data.asset_id,
        Watermark.signature_hash == data.signature_hash,
        Watermark.content_hash == data.content_hash,
        Watermark.status == "active"
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Watermark not found")

    return {
        "verified": True,
        "owner_id": record.owner_id,
        "issued_at": record.issued_at
    }
