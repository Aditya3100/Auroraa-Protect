from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Response, Form
from sqlalchemy.orm import Session
import hashlib

from app.database.database import get_db
from app.models.models import Watermark

from app.crud.watermark_crud import map_content_type
from app.services.watermark.image.image_verifier import verify_self_watermark 
from app.services.watermark.image.image_embedder import embed_watermark_robust
from app.logger import get_current_user, get_username_from_auth

from app.services.watermark.image.image_config import interpret_verification_result, ALGORITHM_VERSION, confidence_to_status
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timezone

waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])

@waterrouter.post("/upload")
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
    # signature_hash = hashlib.sha256(image_bytes).hexdigest()

    watermark = Watermark(
        owner_id=owner_id,
        content_type=content_type,
        mime_type=file.content_type,
        # signature_hash=signature_hash,
        algorithm_version=ALGORITHM_VERSION,
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
            owner_id=owner_id
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

# @waterrouter.post("/verify-public")
# async def Public_verify_image(
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
# ):
#     image_bytes = await file.read()

#     # Heavy verification off event loop
#     raw = await run_in_threadpool(
#         verify_image_owner_robust,
#         image_bytes=image_bytes,
#         db=db
#     )

#     if raw is None:
#         return {
#             "verified": False,
#             "issued_by_auroraa": False,
#             "confidence": 0,
#             "status": "not_verified",
#             "issued_on": None,
#         }

#     confidence = raw["confidence"]
#     status = confidence_to_status(confidence)

#     # 🔹 Resolve issued_on from DB
#     issued_on = None
#     if raw.get("watermark_id"):
#         wm = (
#             db.query(Watermark.created_at)
#             .filter(Watermark.id == raw["watermark_id"])
#             .first()
#         )
#         if wm and wm.created_at:
#             issued_on = wm.created_at.astimezone(timezone.utc).isoformat()

#     response = {
#         "verified": status != "not_verified",
#         "issued_by_auroraa": status != "not_verified",
#         "confidence": round(confidence, 3),
#         "status": status,
#         "issued_on": issued_on,
#     }

#     # 🔹 Public username ONLY (never owner_id)
#     owner_id = raw.get("owner_id")
#     if owner_id:
#         try:
#             username = await get_username_from_auth(owner_id)
#             if username:
#                 response["username"] = username
#         except Exception as e:
#             print("Auth lookup failed:", e)

#     return response

@waterrouter.post("/verify")
async def verify_self(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_bytes = await file.read()

    owner_id = current_user.get("user_id")

    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Run secure self verification (HMAC-bound)
    raw = verify_self_watermark(
        image_bytes,
        owner_id,       # pass owner for crypto binding
    )

    return interpret_verification_result(raw)
