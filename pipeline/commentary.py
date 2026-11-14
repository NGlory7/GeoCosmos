"""Gemini yorumcu: analogs/*.geojson içindeki ilk commentary.top_k adaya ai_comment yazar.

Kurallar (ARCHITECTURE.md > Gemini kullanımı):
- Sadece verilen değerleri kullan, yeni sayı ekleme; benzemeyen yönleri ve kopma noktalarını yaz.
- Yorumda motorun JSON'unda olmayan bir sayı varsa yorum yeniden üretilir (commentary.max_retries);
  yine olmazsa ai_comment boş bırakılır. Boş yorum, uydurma yorumdan iyidir.
- Geçmiş testler Gemini'ye yazdırılmaz (elle ve kaynaklı girilir).
- Aynı analog JSON'u için sonuç data/processed/commentary_cache.json'dan döner (kota korunur).
- Yeniden üretimde (make data) mevcut yorumlar korunur: keşif dosyaları yeniden yazılmadan önce
  existing_comments() ile toplanır; istem (prompt) birebir aynıysa yorum yeniden kullanılır, Gemini
  çağrılmaz. Önbellek dosyası olmayan bilgisayarda da GitHub'daki yorumlar silinmez.
- GEMINI_API_KEY yoksa yeni yorum üretilmez; korunan yorumlar yine yazılır.
- Günlük kota (ücretsiz: 500 istek/gün) dolarsa beklenmez: kalanlar boş kalır, ertesi gün yeniden çalıştırılır.
- Her istekte 60 sn zaman sınırı var; takılan istek yeniden denenir.

Kullanım:  python -m pipeline.commentary
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
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


def _r(x):
    """Gemini'ye giden sayıyı 2 ondalığa yuvarlar. Yuvarlanmamış değer (0.9502831390049846) yoruma
    olduğu gibi kopyalanıyordu; uydurma sayı kontrolü de bu yuvarlanmış değerlere göre yapılır."""
    return round(x, 2) if isinstance(x, float) else x


def payload_for(props: dict, labels: dict[str, str]) -> dict:
    """Gemini'ye giden, yoruma gereken alanlar (geçmiş testler ve kimlikler hariç)."""
    return {
        "bolge": props["name"],
        "toplam_skor": _r(props["score_total"]),
        "boyut_skorlari": {k: _r(v) for k, v in props["scores"].items() if v is not None},
        "parametreler": [{"ad": labels.get(p["key"], p["key"]), "dunya": _r(p["earth"]), "hedef": _r(p["target"]),
                          "benziyor": p["match"], "kaynak": p["source"]} for p in props["params"]],
        "operasyon": props.get("ops_tags", {}),
        "yeni_aday": props["is_new"],
    }


_last_call = 0.0


class DailyQuotaExhausted(RuntimeError):
    """Günlük istek kotası (ücretsiz: 500/gün) doldu; beklemek anlamsız, ertesi gün yeniden çalıştır."""


def _is_daily_quota(err: Exception) -> bool:
    msg = str(err)
    return "per day" in msg.lower() or "PerDay" in msg


def _retry_delay_s(err: Exception, default: float) -> float:
    """429 hatasındaki "retry in 5.0s" / retryDelay değerini okur; bulamazsa default."""
    m = re.search(r"retry in ([\d.]+)s|'retryDelay': '([\d.]+)s'", str(err))
    return float(m.group(1) or m.group(2)) + 1 if m else default


def gemini_generate(prompt: str) -> str:
    """Ücretsiz kota dakikada sınırlı istek verir (gemini-3.5-flash-lite: 15). İstekler arasında
    commentary.min_interval_s beklenir; yine de 429 (kota) ya da 500/503 (geçici yoğunluk) gelirse
    beklenip yeniden denenir (commentary.rate_limit_retries)."""
    global _last_call
    from google import genai  # sadece gerektiğinde yükle
    from google.genai import errors

    import httpx

    cfg = load_grid_config()["commentary"]
    # Zaman sınırı olmadan takılan bir istek tüm üretimi sessizce durduruyordu (60 sn, ms cinsinden).
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options={"timeout": 60_000})
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    for attempt in range(cfg.get("rate_limit_retries", 5) + 1):
        wait = cfg.get("min_interval_s", 0) - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        try:
            return client.models.generate_content(model=model, contents=prompt).text.strip()
        except errors.APIError as e:
            # 429: kota; 500/503: Gemini tarafında geçici yoğunluk ("high demand"). İkisi de beklenip denenir.
            # Günlük kota ise saatler sonra açılır: beklemeden durulur.
            if e.code == 429 and _is_daily_quota(e):
                raise DailyQuotaExhausted(str(e)[:300]) from e
            if e.code not in (429, 500, 503) or attempt == cfg.get("rate_limit_retries", 5):
                raise
            time.sleep(_retry_delay_s(e, default=30 * (attempt + 1)))
        except httpx.TimeoutException:
            if attempt == cfg.get("rate_limit_retries", 5):
                raise
    raise RuntimeError("ulaşılamaz")


def prompt_for(props: dict) -> tuple[str, set[str]]:
    """Analog için Gemini istemi ve yorumda izin verilen sayılar."""
    targets, profiles = load_targets(), load_profiles()
    labels = {k: p.label for k, p in load_parameters().items()}
    target, profile = targets[props["target_id"]], profiles.get(props["test_id"])
    payload = payload_for(props, labels)
    breakdown = "; ".join(NOTES[target.body][k] for k in props["breakdown"] if k in NOTES[target.body])
    prompt = PROMPT.format(target_name=target.name, body="Ay" if target.body == "moon" else "Mars",
                           test_label=profile.label if profile else props["test_id"],
                           breakdown=breakdown, payload=json.dumps(payload, ensure_ascii=False))
    return prompt, allowed_numbers(payload) | allowed_numbers({"b": breakdown})


def _prompt_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def existing_comments(analog_dir: Path = ANALOG_DIR) -> dict[str, str]:
    """Diskteki dolu yorumlar, istem özetine göre. Keşif dosyaları yeniden yazılmadan ÖNCE çağrılır.
    Uydurma sayı içeren eski yorum alınmaz (kurallar değiştiyse yeniden üretilsin)."""
    kept: dict[str, str] = {}
    for path in sorted(analog_dir.glob("*.geojson")):
        try:
            feats = json.loads(path.read_text(encoding="utf-8"))["features"]
        except (json.JSONDecodeError, KeyError):
            continue
        for feat in feats:
            props = feat.get("properties", {})
            text = props.get("ai_comment") or ""
            if not text:
                continue
            try:
                prompt, allowed = prompt_for(props)
            except KeyError:  # hedef ya da test artık yok
                continue
            if not invented_numbers(text, allowed):
                kept[_prompt_key(prompt)] = text
    return kept


def comment_for(props: dict, generate: Callable[[str], str] | None, cache: dict, max_retries: int,
                kept: dict[str, str] | None = None) -> str:
    prompt, allowed = prompt_for(props)
    if kept and _prompt_key(prompt) in kept:
        return kept[_prompt_key(prompt)]
    key = hashlib.sha256((os.getenv("GEMINI_MODEL", "") + prompt).encode()).hexdigest()
    if key in cache:
        return cache[key]
    if generate is None:
        return ""
    text = ""
    for _ in range(max_retries + 1):
        candidate = generate(prompt)
        if not invented_numbers(candidate, allowed):
            text = candidate
            break
    cache[key] = text
    return text


def add_comments(analog_dir: Path = ANALOG_DIR, generate: Callable[[str], str] | None = None,
                 cache_path: Path = CACHE_PATH, kept: dict[str, str] | None = None,
                 allow_generate: bool = True) -> dict:
    """Dönüş: {"written": n, "empty": n, "kept": n, "skipped": sebep|None}.
    kept: existing_comments() çıktısı; allow_generate=False ya da anahtar yoksa sadece korunanlar yazılır."""
    load_dotenv(ROOT / ".env")
    if kept is None:  # tek başına çalıştırıldı (python -m pipeline.commentary): diskteki yorumları koru
        kept = existing_comments(analog_dir)
    skipped = None
    if not allow_generate:
        generate, skipped = None, "yeni yorum üretimi kapalı (--skip-commentary)"
    elif generate is None:
        if os.getenv("GEMINI_API_KEY"):
            generate = gemini_generate
        else:
            skipped = "GEMINI_API_KEY yok"
    if generate is None and not kept:
        return {"written": 0, "empty": 0, "kept": 0, "skipped": skipped}
    cfg = load_grid_config()["commentary"]
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        cache = {}
    written = empty = reused = 0
    for path in sorted(analog_dir.glob("*.geojson")):
        fc = json.loads(path.read_text(encoding="utf-8"))
        for feat in fc["features"][: cfg["top_k"]]:
            if kept and _prompt_key(prompt_for(feat["properties"])[0]) in kept:
                reused += 1
            try:
                text = comment_for(feat["properties"], generate, cache, cfg["max_retries"], kept)
            except DailyQuotaExhausted:
                # Kalan adaylar için sadece korunan/önbellekteki yorumlar; boşlar önbelleğe yazılmaz.
                generate, skipped = None, "Gemini günlük kotası doldu; yarın yeniden çalıştır"
                text = comment_for(feat["properties"], None, cache, cfg["max_retries"], kept)
            feat["properties"]["ai_comment"] = text
            written += bool(text)
            empty += not text
        path.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"written": written, "empty": empty, "kept": reused, "skipped": skipped}


if __name__ == "__main__":
    print(add_comments())
