from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database.database import Base
import uuid
import enum
from sqlalchemy import (
    Column, String, Float, Text, Enum, Boolean, ForeignKey,
    Integer, DateTime, CHAR, Table, JSON
)
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
import uuid
import enum
from sqlalchemy import Enum as SqlEnum
from app.database.database import Base

class Watermark(Base):
    __tablename__ = "watermarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(255), index=True, nullable=False)
    owner_id = Column(String(255), nullable=False)
    issued_at = Column(DateTime, nullable=False)

    signature_hash = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False)

    algorithm_version = Column(String(20), default="v1")
    status = Column(String(20), default="active")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )