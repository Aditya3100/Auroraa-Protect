from pydantic import BaseModel
from datetime import datetime

class WatermarkCreate(BaseModel):
    asset_id: str
    owner_id: str
    issued_at: datetime
    signature_hash: str
    content_hash: str

class WatermarkVerify(BaseModel):
    asset_id: str
    signature_hash: str
    content_hash: str
