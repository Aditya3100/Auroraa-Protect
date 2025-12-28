from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

# ---------- Create ----------
class WatermarkCreate(BaseModel):
    asset_id: str
    owner_id: str

    # semantic category: image | video | audio | document
    content_type: Literal["image", "video", "audio", "document"]

    # exact MIME type
    mime_type: str

    issued_at: datetime
    signature_hash: str
    content_hash: str
    algorithm_version: str = "v1"


# ---------- Response ----------
class WatermarkResponse(BaseModel):
    id: str
    asset_id: str
    owner_id: str

    content_type: Literal["image", "video", "audio", "document"]
    mime_type: str

    issued_at: datetime
    signature_hash: str
    content_hash: str
    algorithm_version: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
