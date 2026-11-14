"""Gemini tercümanı: serbest metni parametre ağırlıklarına çevirir. Sayı/sıralama üretmez.

Aynı metin için sonuç data/processed/gemini_cache.json dosyasından döner.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

from core.profiles import Parameter

CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "gemini_cache.json"
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class GeminiError(RuntimeError):
    pass


class _Weight(BaseModel):
    key: str
    weight: float


class _Translation(BaseModel):
    weights: list[_Weight]
    unsupported: list[str]


PROMPT = """Sen bir tercümansın. Kullanıcı Ay veya Mars için bir test senaryosu yazdı.
Görevin: senaryoyu aşağıdaki parametrelerin ağırlıklarına çevirmek.

Kurallar:
- Sadece listedeki parametre anahtarlarını kullan. Yeni anahtar uydurma.
- Ağırlıklar 0 ile 1 arasında; senaryo için önemli olana yüksek ver, ilgisizleri yazma.
- Dünya'da karşılığı olmayan istekleri (düşük yerçekimi, vakum, yüksek radyasyon gibi)
  "unsupported" listesine kısa Türkçe ifadeyle yaz.
- Yer adı, skor veya sıralama üretme.

Parametreler:
{params}

Senaryo:
{text}
"""


def _cache_key(text: str, params: dict[str, Parameter]) -> str:
    raw = MODEL + "|" + ",".join(sorted(params)) + "|" + text.strip().lower()
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def translate(text: str, params: dict[str, Parameter]) -> dict:
    """{"weights": {key: float}, "unsupported": [str]} döndürür (henüz normalize edilmemiş)."""
    key = _cache_key(text, params)
    cache = _read_cache()
    if key in cache:
        return cache[key]

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError("GEMINI_API_KEY tanımlı değil")

    from google import genai  # sadece gerektiğinde yükle

    param_list = "\n".join(f"- {p.key}: {p.label}" for p in params.values())
    try:
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=MODEL,
            contents=PROMPT.format(params=param_list, text=text),
            config={"response_mime_type": "application/json", "response_schema": _Translation},
        )
        parsed = _Translation.model_validate_json(resp.text)
    except Exception as e:  # ağ, kota, şema hatası
        raise GeminiError(str(e)) from e

    result = {
        "weights": {w.key: w.weight for w in parsed.weights},
        "unsupported": parsed.unsupported,
    }
    cache[key] = result
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
