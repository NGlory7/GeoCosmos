"""FastAPI uygulaması: /scenario (Gemini tercüman + motor)."""
from fastapi import FastAPI

app = FastAPI(title="GeoCosmos API")


@app.post("/scenario")
def scenario(payload: dict) -> dict:
    # TODO: Gemini ile senaryoyu ağırlıklara çevir, benzerlik motorunu çalıştır
    return {"status": "not_implemented", "input": payload}
