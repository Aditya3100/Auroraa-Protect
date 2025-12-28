from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import hashlib

from app.database.database import get_db
from app.models.models import Watermark
from app.services.watermark.watermark_content_engine import (
    embed_watermark,
    hash_content
)
from app.crud.watermark_crud import map_content_type


waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])


@waterrouter.post("/upload")
async def upload_and_watermark(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    db: Session = Depends(get_db)
):
    raw = await file.read()

    content_hash = hash_content(raw)
    signature = hashlib.sha256(
        (content_hash + owner_id).encode()
    ).hexdigest()

    asset_id = str(uuid.uuid4())

    mime = (file.content_type or "application/octet-stream") \
        .split(";")[0].lower()

    try:
        watermarked = embed_watermark(
            raw,
            mime,
            asset_id,
            signature
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    record = Watermark(
        asset_id=asset_id,
        owner_id=owner_id,
        content_type=map_content_type(mime),
        mime_type=mime,
        issued_at=datetime.utcnow(),
        content_hash=content_hash,
        signature_hash=signature,
        status="active"
    )

    db.add(record)
    db.commit()

    return Response(
        content=watermarked,
        media_type=mime,
        headers={
            "X-Auroraa-Asset-ID": asset_id
        }
    )


@waterrouter.post("/verify")
async def verify_watermark(
    file: UploadFile = File(...),
    asset_id: str = Form(...),
    db: Session = Depends(get_db)
):
    raw = await file.read()
    content_hash = hash_content(raw)

    record = db.query(Watermark).filter(
        Watermark.asset_id == asset_id,
        Watermark.content_hash == content_hash,
        Watermark.status == "active"
    ).first()

    if not record:
        return {"verified": False}

    return {
        "verified": True,
        "owner_id": record.owner_id,
        "content_type": record.content_type,
        "mime_type": record.mime_type,
        "issued_at": record.issued_at,
        "algorithm_version": record.algorithm_version
    }
