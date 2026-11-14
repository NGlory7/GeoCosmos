"""Gemini yorumcu: analogs/*.geojson içindeki ilk commentary.top_k adaya ai_comment yazar.

Kurallar (ARCHITECTURE.md > Gemini kullanımı):
- Sadece verilen değerleri kullan, yeni sayı ekleme; benzemeyen yönleri ve kopma noktalarını yaz.
- Yorumda motorun JSON'unda olmayan bir sayı varsa yorum yeniden üretilir (commentary.max_retries);
  yine olmazsa ai_comment boş bırakılır. Boş yorum, uydurma yorumdan iyidir.
- Geçmiş testler Gemini'ye yazdırılmaz (elle ve kaynaklı girilir).
- Aynı analog JSON'u için sonuç data/processed/commentary_cache.json'dan döner (kota korunur).
- GEMINI_API_KEY yoksa adım atlanır, dosyalar değişmez.

Kullanım:  python -m pipeline.commentary
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from core.breakdown import NOTES
from core.profiles import load_grid_config, load_parameters, load_profiles, load_targets

ROOT = Path(__file__).resolve().parent.parent
ANALOG_DIR = ROOT / "frontend" / "public" / "data" / "analogs"
CACHE_PATH = ROOT / "data" / "processed" / "commentary_cache.json"
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")

PROMPT = """Sen bir gezegen bilimi editörüsün. Aşağıdaki JSON, Dünya'daki bir bölgenin {target_name}
({body}) hedefine "{test_label}" testi için ne kadar benzediğini gösteren motor çıktısıdır.

1-2 kısa paragraf Türkçe açıklama yaz:
- Neden iyi bir test sahası olabileceğini (benzeyen parametreler, "match": true).
- Nerede benzemediğini (benzemeyen parametreler) ve kopma noktalarını: {breakdown}.
Kurallar:
- SADECE JSON'daki sayıları kullan. Yeni sayı, yüzde, tarih, mesafe ya da yer adı ekleme.
- Geçmiş test, görev ya da makale anma.
- Abartma; "en iyi", "kusursuz" gibi ifadeler kullanma.

JSON:
{payload}
"""


def _canon(x: float) -> set[str]:
    out = set()
    for d in (0, 1, 2, 3):
        r = round(x, d)
        out.add(f"{r:.{d}f}")
        if d == 0:
            out.add(str(int(r)))
    return out


def allowed_numbers(payload: dict) -> set[str]:
    nums: set[str] = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            nums.update(_canon(float(v)))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            for m in NUMBER.findall(v):
                nums.update(_canon(float(m.replace(",", "."))))
    walk(payload)
    return nums


def invented_numbers(text: str, allowed: set[str]) -> list[str]:
    """Metinde geçen ama izinli kümede olmayan sayılar (Türkçe ondalık virgül desteklenir)."""
    bad = []
    for m in NUMBER.findall(text):
        v = float(m.replace(",", "."))
        if not (_canon(v) & allowed):
            bad.append(m)
    return bad


def payload_for(props: dict, labels: dict[str, str]) -> dict:
    """Gemini'ye giden, yoruma gereken alanlar (geçmiş testler ve kimlikler hariç)."""
    return {
        "bolge": props["name"],
        "toplam_skor": props["score_total"],
        "boyut_skorlari": {k: v for k, v in props["scores"].items() if v is not None},
        "parametreler": [{"ad": labels.get(p["key"], p["key"]), "dunya": p["earth"], "hedef": p["target"],
                          "benziyor": p["match"], "kaynak": p["source"]} for p in props["params"]],
        "operasyon": props.get("ops_tags", {}),
        "yeni_aday": props["is_new"],
    }


def gemini_generate(prompt: str) -> str:
    from google import genai  # sadece gerektiğinde yükle

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return client.models.generate_content(model=model, contents=prompt).text.strip()


def comment_for(props: dict, generate: Callable[[str], str], cache: dict, max_retries: int) -> str:
    targets, profiles = load_targets(), load_profiles()
    labels = {k: p.label for k, p in load_parameters().items()}
    target, profile = targets[props["target_id"]], profiles.get(props["test_id"])
    payload = payload_for(props, labels)
    breakdown = "; ".join(NOTES[target.body][k] for k in props["breakdown"] if k in NOTES[target.body])
    prompt = PROMPT.format(target_name=target.name, body="Ay" if target.body == "moon" else "Mars",
                           test_label=profile.label if profile else props["test_id"],
                           breakdown=breakdown, payload=json.dumps(payload, ensure_ascii=False))
    key = hashlib.sha256((os.getenv("GEMINI_MODEL", "") + prompt).encode()).hexdigest()
    if key in cache:
        return cache[key]
    allowed = allowed_numbers(payload) | allowed_numbers({"b": breakdown})
    text = ""
    for _ in range(max_retries + 1):
        candidate = generate(prompt)
        if not invented_numbers(candidate, allowed):
            text = candidate
            break
    cache[key] = text
    return text


def add_comments(analog_dir: Path = ANALOG_DIR, generate: Callable[[str], str] | None = None,
                 cache_path: Path = CACHE_PATH) -> dict:
    """Dönüş: {"written": n, "empty": n, "skipped": sebep|None}."""
    load_dotenv()
    if generate is None:
        if not os.getenv("GEMINI_API_KEY"):
            return {"written": 0, "empty": 0, "skipped": "GEMINI_API_KEY yok"}
        generate = gemini_generate
    cfg = load_grid_config()["commentary"]
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    written = empty = 0
    for path in sorted(analog_dir.glob("*.geojson")):
        fc = json.loads(path.read_text(encoding="utf-8"))
        for feat in fc["features"][: cfg["top_k"]]:
            text = comment_for(feat["properties"], generate, cache, cfg["max_retries"])
            feat["properties"]["ai_comment"] = text
            written += bool(text)
            empty += not text
        path.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"written": written, "empty": empty, "skipped": None}


if __name__ == "__main__":
    print(add_comments())
