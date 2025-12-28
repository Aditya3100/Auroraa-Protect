from fastapi import FastAPI
from app.database.database import engine, Base
from app.routes.watermark_routes import waterrouter

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auroraa Sentinel")

app.include_router(waterrouter)
