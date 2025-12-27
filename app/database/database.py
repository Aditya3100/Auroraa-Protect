from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv  

load_dotenv(dotenv_path=r"C:\Users\ghara\OneDrive\Desktop\parth\auroraa sentinal\.env")

# MySQL DB connection string
DATABASE_URL = os.getenv("DATABASE_URL")
# Create SQLAlchemy engine  by removing ssl_args
engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print(os.getenv("DATABASE_URL"))