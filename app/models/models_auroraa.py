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


class RoleEnum(str, enum.Enum):
    user = "user"
    admin = "admin"
    store = "store"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    role = Column(SqlEnum(RoleEnum, native_enum=False), nullable=False, default=RoleEnum.user)
    profileImage = Column(String(255), nullable=True)
    profileImagePublicId = Column(String(255), nullable=True)  
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    location = Column(String(100), nullable=True)
    pincode = Column(CHAR(6), nullable=True)
    gender = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    phone = Column(String(15), nullable=True)
    bio = Column(String(500), nullable=True)
    profile_completion = Column(Integer, default=0)
    isActive = Column(Boolean, default=False)         
    isAgreedtoTC = Column(Boolean, default=False)         
 
