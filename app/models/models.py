from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
import uuid
from app.database.database import Base


class Watermark(Base):
    __tablename__ = "watermarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    owner_id = Column(String(36), nullable=False, index=True)

    content_type = Column(String(20), nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)

    signature_hash = Column(String(64), nullable=True)
    content_hash = Column(String(64), nullable=True)

    algorithm_version = Column(String(20), nullable=False, default="v1")
    status = Column(String(20), nullable=False, default="active")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_watermark_verify",
            "id",            
            "content_hash",
            "status"
        ),
    )
