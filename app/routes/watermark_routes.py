from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
import hashlib

from app.database.database import get_db
from app.models.models import Watermark

from app.crud.watermark_crud import map_content_type
from app.services.watermark.dct_dwt.dct_dwt_verifier import verify_image_owner_robust, verify_self_watermark
from app.services.watermark.dct_dwt.dct_dwt_embedder import embed_watermark_robust
from app.logger import get_current_user

from app.services.watermark.dct_dwt.watermark_config import interpret_verification_result, interpret_verification_result_self

waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])

@waterrouter.post("/embed")
async def embed_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner_id = current_user["user_id"]
    if not owner_id:
        raise HTTPException(status_code=400, detail="owner_id is required")

    mime = (file.content_type or "").lower()
    content_type = map_content_type(mime)
    if not content_type:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    image_bytes = await file.read()
    signature_hash = hashlib.sha256(image_bytes).hexdigest()

    watermark = Watermark(
        owner_id=owner_id,
        content_type=content_type,
        mime_type=file.content_type,
        signature_hash=signature_hash,
        algorithm_version="v2-dbscan",
        status="active",
    )

    try:
        db.add(watermark)
        db.commit()
        db.refresh(watermark)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="DB error")

    try:
        watermarked_bytes = embed_watermark_robust(
            image_bytes=image_bytes,
            watermark_id=watermark.id,
        )
    except Exception as e:
        db.delete(watermark)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=watermarked_bytes,
        media_type="image/jpeg",
        headers={
            "X-Watermark-ID": watermark.id,
            "X-Owner-ID": watermark.owner_id,
            "X-Watermark-Mode": "dbscan",
        },
    )

@waterrouter.post("/verify-image")
async def Public_verify_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()

    raw_result = verify_image_owner_robust(
        image_bytes=image_bytes,
        db=db
    )

    return interpret_verification_result(raw_result)

@waterrouter.post("/verify-self")
async def verify_self(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()

    # Only user's own watermarks
    watermark_ids = [
        wm.id for wm in db.query(Watermark).filter(
            Watermark.owner_id == current_user["user_id"],
            Watermark.status == "active",
        ).all()
    ]

    raw = verify_self_watermark(image_bytes, watermark_ids)
    return interpret_verification_result(raw)