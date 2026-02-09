from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Response,
    Form,
)

from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database.database import get_db
from app.models.models import Watermark

from app.crud.watermark_crud import map_content_type
from app.logger import get_current_user

from app.services.watermark.image.image_embedder import embed_watermark
from app.services.watermark.image.image_verifier import verify_watermark

from app.services.watermark.image.image_config import (
    interpret_verification_result,
    ALGORITHM_VERSION,
    previous_epochs,
    current_epoch
)

# ----------------------------------
# Router
# ----------------------------------

waterrouter = APIRouter(
    prefix="/watermark",
    tags=["Watermark"]
)

# ==================================
# EMBED ENDPOINT
# ==================================

@waterrouter.post("/upload")
async def embed_image_watermark(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    owner_id = current_user.get("user_id")

    if not owner_id:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )

    # Validate MIME
    mime = (file.content_type or "").lower()

    content_type = map_content_type(mime)

    if not content_type:
        raise HTTPException(
            status_code=400,
            detail="Unsupported content type"
        )

    image_bytes = await file.read()

    # Generate epoch
    epoch = current_epoch()

    # Create DB record
    watermark = Watermark(
        owner_id=owner_id,
        content_type=content_type,
        mime_type=file.content_type,
        algorithm_version=ALGORITHM_VERSION,
        status="active",
        created_at=datetime.now(timezone.utc),
    )

    try:
        db.add(watermark)
        db.commit()
        db.refresh(watermark)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Database error"
        )

    # Embed watermark
    try:
        watermarked_bytes = embed_watermark(
            image_bytes=image_bytes,
            owner_id=owner_id,
            epoch=epoch,
        )

    except Exception as e:

        # Rollback DB entry
        db.delete(watermark)
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # Return image
    return Response(
        content=watermarked_bytes,
        media_type="image/jpeg",
        headers={
            "X-Watermark-ID": watermark.id,
            "X-Owner-ID": owner_id,
            "X-Watermark-Epoch": epoch,
            "X-Watermark-Mode": "sync",
        },
    )


# ==================================
# VERIFY (PRIVATE / OWNER)
# ==================================

@waterrouter.post("/verify")
async def verify_self(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    owner_id = current_user.get("user_id")

    if not owner_id:
        raise HTTPException(401, "Unauthorized")

    image_bytes = await file.read()

    # Scan all epochs (Owner-Level Uniqueness)
    # We no longer Loop over assets, as the signal is unique to the owner
    
    best = 0.0
    best_raw = None

    epochs = previous_epochs(4)
    # Add current epoch if not in previous (usually previous_epochs returns past 4, we might want current too?)
    # The original code called current_epoch() for embed, and previous_epochs(4) for verify? 
    # Wait, `previous_epochs` implementation:
    # returns 4 epochs ending with current? No, it starts with current usually.
    # Let's check `previous_epochs` in `image_config.py` later if needed, but assuming standard usage.
    # Actually, let's look at `previous_epochs` in `image_config.py` from the view_file earlier.
    # It starts with `now` and goes back. So it includes current.

    for epoch in epochs:

        raw = verify_watermark(
            image_bytes=image_bytes,
            owner_id=owner_id,
            epoch=epoch,
        )

        if raw["confidence"] > best:
            best = raw["confidence"]
            best_raw = raw

    if best_raw is None:
        return interpret_verification_result({
            "verified": False,
            "confidence": 0.0,
            "status": "not_verified"
        })

    return interpret_verification_result(best_raw)
