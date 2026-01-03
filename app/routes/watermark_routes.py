from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
import hashlib

from app.database.database import get_db
from app.models.models import Watermark

from app.crud.watermark_crud import map_content_type
# from app.services.watermark.lsb.watermark_lsb_verify import verify_image_watermark
from app.services.watermark.dct_dwt.dct_dwt_verifier import verify_robust_watermark
from app.services.watermark.dct_dwt.dct_dwt_embedder import embed_robust_watermark
# from app.services.watermark.lsb.watermark_lsb_embedder import embed_watermark



waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])


@waterrouter.post("/upload")
async def upload_and_watermark(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    db: Session = Depends(get_db)
):
    raw = await file.read()
    mime = (file.content_type or "").lower()

    content_type = map_content_type(mime)
    if not content_type:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    try:
        watermarked_bytes = embed_robust_watermark(
            image_bytes=raw,
            owner_id=owner_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watermarking failed: {str(e)}")

    record = Watermark(
        owner_id=owner_id,
        content_type=content_type,
        mime_type=mime,
        status="active"
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return Response(
        content=watermarked_bytes,
        # media_type=mime,
        media_type="image/jpeg",
        headers={
            "X-Auroraa-Asset-ID": str(record.id),
            "Content-Disposition": f'inline; filename="{file.filename}"'
        }
    )

@waterrouter.post("/verify")
async def verify_watermark(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    db: Session = Depends(get_db)  # db can stay if you plan future checks
):
    raw = await file.read()

    try:
        return verify_robust_watermark(
            image_bytes=raw,
            owner_id=owner_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

