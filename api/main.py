"""GeoCosmos canlı API. Hazır sonuçlar statik dosyadır; bu sunucu sadece /scenario içindir.

Çalıştırma:  make api   (ya da: uvicorn api.main:app --reload)
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import scenario

load_dotenv()

app = FastAPI(title="GeoCosmos API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("API_ALLOWED_ORIGIN", "http://localhost:5173")],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(scenario.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
