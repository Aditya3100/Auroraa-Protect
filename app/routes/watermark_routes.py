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

from app.services.watermark.document.doc_crypto import generate_payload
from app.services.watermark.document.doc_embedder import embed_pdf, embed_docx
from app.services.watermark.document.doc_extractor import (
    extract_pdf_bits,
    extract_docx_bits,
)
from app.services.watermark.document.doc_verifier import verify
import uuid, shutil, os
from fastapi.responses import FileResponse
import os

TMP_DIR = "/tmp/watermark"
os.makedirs(TMP_DIR, exist_ok=True)

waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])

@waterrouter.post("/upload")
async def embed_image_watermark(
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
async def verify_image_watermark(
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

@waterrouter.post("/embed/doc")
async def embed_document_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    owner_id = current_user.get("user_id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    filename = (file.filename or "").lower()
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX supported")

    mime_type = (file.content_type or "").lower()
    content_type = map_content_type(mime_type)
    if not content_type:
        raise HTTPException(status_code=400, detail="Unsupported document type")

    watermark = Watermark(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        content_type=content_type,
        mime_type=mime_type,
        algorithm_version=ALGORITHM_VERSION,
        status="active",
    )

    suffix = ".pdf" if filename.endswith(".pdf") else ".docx"
    in_path = f"{TMP_DIR}/{uuid.uuid4()}{suffix}"
    out_path = f"{TMP_DIR}/wm_{uuid.uuid4()}{suffix}"

    with open(in_path, "wb") as f:
        f.write(await file.read())

    payload = generate_payload(watermark)

    if suffix == ".pdf":
        embed_pdf(in_path, out_path, payload, watermark.id)
    else:
        embed_docx(in_path, out_path, payload, watermark.id)

    download_name = f"watermarked_{file.filename}"

    return FileResponse(
        path=out_path,
        filename=download_name,
        media_type=mime_type,
        headers={
            "X-Watermark-ID": watermark.id,
            "X-Algorithm-Version": watermark.algorithm_version,
        }
    )

@waterrouter.post("/verify/doc")
async def verify_document_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    owner_id = current_user.get("user_id")
    if not owner_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    filename = (file.filename or "").lower()
    if not filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX supported")

    mime_type = (file.content_type or "").lower()
    content_type = map_content_type(mime_type)
    if not content_type:
        raise HTTPException(status_code=400, detail="Unsupported document type")

    suffix = ".pdf" if filename.endswith(".pdf") else ".docx"
    path = f"{TMP_DIR}/{uuid.uuid4()}{suffix}"

    with open(path, "wb") as f:
        f.write(await file.read())

    if suffix == ".pdf":
        extracted_bits = extract_pdf_bits(path)
    else:
        extracted_bits = extract_docx_bits(path)

    # 🔐 Verification derives watermark_id internally
    verified, score, watermark_id = verify(
        extracted_bits=extracted_bits,
        owner_id=owner_id,
        algorithm_version=ALGORITHM_VERSION,
    )

    return {
        "verified": verified,
        "confidence": round(score, 3),
        "watermark_id": watermark_id,
    }
