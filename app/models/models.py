from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
import uuid
from app.database.database import Base

class Watermark(Base):
    __tablename__ = "watermarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    asset_id = Column(String(255), nullable=False, index=True)
    owner_id = Column(String(255), nullable=False, index=True)

    content_type = Column(String(100), nullable=False)  # ✅ added

    issued_at = Column(DateTime, nullable=False)

    signature_hash = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False)

    algorithm_version = Column(String(20), nullable=False, default="v1")
    status = Column(String(20), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_watermark_verify",
            "asset_id",
            "signature_hash",
            "content_hash"
        ),
    )
