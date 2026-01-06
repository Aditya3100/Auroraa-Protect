from fastapi import FastAPI
from app.database.database import engine, Base
from app.routes.watermark_routes import waterrouter
from fastapi.middleware.cors import CORSMiddleware
import os
import json

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auroraa Sentinel")

allowed_origins = json.loads(os.getenv("ALLOWED_ORIGIN", "[]"))

app.add_middleware(
    CORSMiddleware,
    # allow_origins= os.getenv("ALLOWED_ORIGIN"),
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(waterrouter)

print(os.getenv("ALLOWED_ORIGIN"))