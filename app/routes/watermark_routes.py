from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
import hashlib

from app.database.database import get_db
from app.models.models import Watermark
from app.services.watermark.lsb.watermark_lsb_embedder import (
    embed_watermark,
    hash_content
)

from app.crud.watermark_crud import map_content_type
from app.services.watermark.lsb.watermark_lsb_verify import verify_image_watermark
from app.services.watermark.dct_dwt.dct_dwt_verifier import verify_robust_watermark
from app.services.watermark.dct_dwt.dct_dwt_embedder import embed_robust_watermark
from app.services.watermark.lsb.watermark_lsb_embedder import embed_watermark



waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])


# @waterrouter.post("/upload")
# async def upload_and_watermark(
#     file: UploadFile = File(...),
#     owner_id: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     raw = await file.read()

#     content_hash = hash_content(raw)
#     signature = hashlib.sha256(
#         (content_hash + owner_id).encode()
#     ).hexdigest()

#     mime = (file.content_type or "application/octet-stream") \
#         .split(";")[0].lower()

#     try:
#         watermarked = embed_watermark(
#             content=raw,
#             mime=mime,
#             signature=signature
#         )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     record = Watermark(
#         owner_id=owner_id,
#         content_type=map_content_type(mime),
#         mime_type=mime,
#         content_hash=content_hash,
#         signature_hash=signature,
#         status="active"
#     )

#     db.add(record)
#     db.commit()
#     db.refresh(record)

#     return Response(
#         content=watermarked,
#         media_type=mime,
#         headers={
#             "X-Auroraa-Asset-ID": record.id
#         }
#     )


# @waterrouter.post("/verify")
# async def verify_watermark(
#     file: UploadFile = File(...),
#     watermark_id: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     raw = await file.read()

#     return verify_image_watermark(
#         image_bytes=raw,
#         watermark_id=watermark_id,
#         db=db
#     )


@waterrouter.post("/upload")
async def upload_and_watermark(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    mode: str = Form("lsb"),   # 👈 NEW
    db: Session = Depends(get_db)
):
    raw = await file.read()

    mime = (file.content_type or "").lower()

    record = Watermark(
        owner_id=owner_id,
        content_type=map_content_type(mime),
        mime_type=mime,
        status="active"
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    if mode == "robust":
        watermarked = embed_robust_watermark(raw, record.id)
    else:
        watermarked = embed_watermark(raw, mime, record.id)

    return Response(
        content=watermarked,
        media_type=mime,
        headers={"X-Auroraa-Asset-ID": record.id}
    )


@waterrouter.post("/verify")
async def verify_watermark(
    file: UploadFile = File(...),
    watermark_id: str = Form(...),
    mode: str = Form("robust"),
    db: Session = Depends(get_db)
):
    raw = await file.read()

    if mode == "robust":
        return verify_robust_watermark(raw, watermark_id)
    else:
        return verify_image_watermark(raw, watermark_id, db)
