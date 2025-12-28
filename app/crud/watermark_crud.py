from sqlalchemy.orm import Session
from app.models.models import Watermark
from app.schemas.watermark_schemas import WatermarkCreate

# ---------- CONTENT TYPE MAPPER ----------
def map_content_type(mime: str) -> str:
    mime = mime.split(";")[0].lower()

    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"
