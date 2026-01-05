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
from app.logger import get_current_user


waterrouter = APIRouter(prefix="/watermark", tags=["Watermark"])

@waterrouter.post("/upload")
async def upload_and_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    owner_id = current_user["user_id"]

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
        media_type="image/jpeg",
        headers={
            "X-Auroraa-Asset-ID": str(record.id),
            "Content-Disposition": f'inline; filename="{file.filename}"'
        }
    )

@waterrouter.post("/verify")
async def verify_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    owner_id = current_user["user_id"]

    raw = await file.read()

    try:
        result = verify_robust_watermark(
            image_bytes=raw,
            owner_id=owner_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # -------------------------------
    # UX + Platform interpretation
    # -------------------------------
    confidence = result["confidence"]
    status = result["status"]

    if status == "verified":
        ux_label = "Verified Original"
        ux_message = (
            "This image is verified as authentic and issued by Auroraa for this owner."
        )
    elif status == "most":
        ux_label = "Verified, but Modified"
        ux_message = (
            "This image is verified as authentic and issued by Auroraa, "
            "but it has been modified (for example, shared or compressed)."
        )
    elif status == "likely":
        ux_label = "Likely Authentic"
        ux_message = (
            "This image likely belongs to this owner, but it has been heavily modified."
        )
    else:
        ux_label = "Not Verified"
        ux_message = (
            "This image could not be verified as authentic."
        )

    return {
        "verified": result["verified"],
        "issued_by_auroraa": result["verified"],  # 🔐 platform verification
        "confidence": confidence,
        "status": status,
        "message": {
            "label": ux_label,
            "message": ux_message
        }
    }


