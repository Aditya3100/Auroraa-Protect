from fastapi import FastAPI
from app.database.database import engine, Base
from app.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auroraa Sentinel")

app.include_router(router)
