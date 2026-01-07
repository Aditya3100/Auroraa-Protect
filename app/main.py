# from fastapi import FastAPI
# from app.database.database import engine, Base
# from app.routes.watermark_routes import waterrouter
# from fastapi.middleware.cors import CORSMiddleware
# import os
# import json

# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="Auroraa Sentinel")

# allowed_origins = json.loads(os.getenv("ALLOWED_ORIGIN", "[]"))

# app.add_middleware(
#     CORSMiddleware,
#     # allow_origins= os.getenv("ALLOWED_ORIGIN"),
#     allow_origins=allowed_origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# app.include_router(waterrouter)

# print(os.getenv("ALLOWED_ORIGIN"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import engine, Base
from app.routes.watermark_routes import waterrouter
import os
import json

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auroraa Sentinel")

# Load ALLOWED_ORIGIN safely
raw = os.getenv("ALLOWED_ORIGIN", "")

allowed_origins = []

if raw:
    try:
        # Try parsing as JSON (preferred)
        parsed = json.loads(raw)

        # Ensure it is actually a list
        if isinstance(parsed, list):
            allowed_origins = parsed
        else:
            print("ALLOWED_ORIGIN JSON is not a list – falling back to string parsing")
            allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]

    except json.JSONDecodeError:
        # Fallback: treat as comma-separated string
        print("Invalid JSON in ALLOWED_ORIGIN – using comma-separated parsing")
        allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]
else:
    # Default if nothing provided
    allowed_origins = []

# If still empty, optionally allow all during dev
if not allowed_origins:
    print("No ALLOWED_ORIGIN configured – defaulting to allow all origins")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=allowed_origins,
    allow_origins=["https://www.auroraa.in","https://www.staging.auroraa.in","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(waterrouter)

print("Final allowed origins:", allowed_origins)
