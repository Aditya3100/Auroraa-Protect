from pydantic import BaseModel
from datetime import datetime
from typing import Literal


# ---------- Internal Create (optional, if you still want it) ----------
class WatermarkCreate(BaseModel):
    owner_id: str
    content_type: Literal["image", "video", "audio", "document"]
    mime_type: str
    signature_hash: str
    content_hash: str
    algorithm_version: str = "v1"


# ---------- API Response ----------
class WatermarkResponse(BaseModel):
    id: str                     # canonical asset ID
    owner_id: str

    content_type: Literal["image", "video", "audio", "document"]
    mime_type: str

    signature_hash: str
    content_hash: str
    algorithm_version: str
    status: str
    created_at: datetime        # issuance time

    class Config:
        from_attributes = True

class WatermarkUploadResponse(BaseModel):
    id: str
    mime_type: str
    created_at: datetime
