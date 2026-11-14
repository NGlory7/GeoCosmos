"""GeoCosmos canlı API. Hazır sonuçlar statik dosyadır; bu sunucu sadece /scenario içindir.

Çalıştırma:  make api   (ya da: uvicorn api.main:app --reload)
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import scenario

load_dotenv()

DEFAULT_ORIGIN = "http://localhost:5173"


def parse_origins(raw: str | None) -> list[str]:
    """API_ALLOWED_ORIGIN: virgülle ayrılmış adresler. Boşluk ve sondaki '/' temizlenir.

    Tarayıcı Origin başlığını '/' olmadan gönderir; 'https://x.app/' yazılırsa eşleşmez.
    """
    origins = [o.strip().rstrip("/") for o in (raw or "").split(",")]
    return [o for o in origins if o] or [DEFAULT_ORIGIN]


app = FastAPI(title="GeoCosmos API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_origins(os.getenv("API_ALLOWED_ORIGIN")),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(scenario.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
