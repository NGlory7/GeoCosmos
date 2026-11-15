"""Aday karelere yer adı: ters coğrafi kodlama (OpenStreetMap Nominatim) -> data/processed/place_names.json.

Ağ isteği sadece bu betik açıkça çalıştırılınca yapılır. Keşif (pipeline/discovery.py) ve /scenario
adları sadece önbellekten okur: CI ve ekip ağsız çalışır, önbellekte olmayan kare koordinatla görünür.

Nominatim kullanım kuralları: saniyede en fazla 1 istek, tanımlayıcı User-Agent, sonuçlar önbelleğe
alınır (https://operations.osmfoundation.org/policies/nominatim/). Her kare için iki istek (tr, en).
Veri: © OpenStreetMap katkıcıları, ODbL.

Kullanım:
  python -m pipeline.placenames           # analog dosyalarındaki eksik kareleri çeker, dosyalara yazar
  python -m pipeline.placenames --offline # ağ isteği yok; sadece önbellekteki adları dosyalara yazar
"""
from __future__ import annotations

import argparse
import json
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from core.schemas import Place

ROOT =Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "processed" / "place_names.json"
ANALOG_DIR = ROOT / "frontend" / "public" / "data" / "analogs"
URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "analog-site-research/0.1 (batch reverse geocoding, cached)"
MIN_INTERVAL_S = 1.1
ZOOM = 10  # ilçe/il düzeyi: 25 km'lik kare için yeterince ayrıntılı

# En ayrıntılıdan genele; ilk bulunan yerel birim + il/eyalet + ülke kullanılır.
LOCAL_KEYS = ("county", "state_district", "district", "municipality", "city", "town", "region", "province")
STATE_KEYS = ("state", "territory", "archipelago")


def _parts(address: dict) -> list[str | None]:
    """[yerel birim, il/eyalet, ülke]: Nominatim adres alanlarından."""
    return [next((address[k] for k in LOCAL_KEYS if address.get(k)), None),
            next((address[k] for k in STATE_KEYS if address.get(k)), None),
            address.get("country")]


def is_latin(text: str) -> bool:
    """Harflerin hepsi Latin alfabesinden mi (Türkçe karakterler dahil)."""
    return all("LATIN" in unicodedata.name(c, "") for c in text if c.isalpha())


def label(address: dict, fallback: dict | None = None) -> str | None:
    """Kısa etiket: "Keriya, Sincan, Çin". Tekrarlar atılır.

    fallback (İngilizce adres) verilirse, Latin harfli olmayan parça onun karşılığıyla değiştirilir:
    Türkçe adı olmayan yerlerde Nominatim yerel yazıyı (ör. Çince, Uygurca) döndürür."""
    parts = _parts(address)
    if fallback is not None:
        alt = _parts(fallback)
        parts = [p if (p is None or is_latin(p)) else (a or p) for p, a in zip(parts, alt)]
    out: list[str] = []
    for p in parts:
        if p and p not in out:
            out.append(p)
    return ", ".join(out) or None


def load_cache(path: Path = CACHE_PATH) -> dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(cache: dict[str, dict], path: Path = CACHE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1), encoding="utf-8")


_last = 0.0


def reverse(lat: float, lon: float, lang: str) -> dict:
    """Tek ters coğrafi kodlama isteği (hız sınırına uyar): adres alanları. Sonuç yoksa {}."""
    global _last
    wait = MIN_INTERVAL_S - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    q = urllib.parse.urlencode({"format": "jsonv2", "lat": f"{lat:.4f}", "lon": f"{lon:.4f}",
                                "zoom": ZOOM, "addressdetails": 1, "accept-language": lang})
    req = urllib.request.Request(f"{URL}?{q}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    finally:
        _last = time.monotonic()
    return {} if "error" in data else (data.get("address") or {})


def latin_only(text: str | None) -> str | None:
    """Etiketin her parçasından Latin dışı kelimeleri atar: OSM bazı adları iki yazıyla tutar
    ("Ad Dabbah الدبة", "Halfa - حلفا"). Tamamen Latin dışı parça düşer; hiçbir şey kalmazsa None."""
    if not text:
        return None
    parts = []
    for part in text.split(","):
        words = [w for w in part.split() if is_latin(w) and any(c.isalpha() for c in w)]
        clean = " ".join(words).strip(" -–")
        if clean and clean not in parts:
            parts.append(clean)
    return ", ".join(parts) or None


def place_for(cell_id: str, cache: dict[str, dict]) -> dict | None:
    """Önbellekteki yer adı {"tr", "en"} (Latin harflerle); yoksa ya da çözülemediyse None."""
    p = cache.get(cell_id) or {}
    tr, en = latin_only(p.get("tr")), latin_only(p.get("en"))
    return {"tr": tr, "en": en} if tr and en else None


def attach_places(analogs, cache: dict[str, dict] | None = None) -> None:
    """Analog nesnelerine önbellekteki yer adını yazar (yerinde). Ağ isteği yapmaz."""
    cache = load_cache() if cache is None else cache
    for a in analogs:
        p = place_for(a.id, cache)
        if p:
            a.place = Place(**p)


def analog_cells(analog_dir: Path = ANALOG_DIR) -> dict[str, tuple[float, float]]:
    cells: dict[str, tuple[float, float]] = {}
    for path in sorted(analog_dir.glob("*.geojson")):
        for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
            p = f["properties"]
            cells[p["id"]] = (p["lat"], p["lon"])
    return cells


def fetch_missing(cells: dict[str, tuple[float, float]], cache: dict[str, dict],
                  save_every: int = 20) -> int:
    """Önbellekte olmayan kareleri çeker; ara ara kaydeder (kesilirse kaldığı yerden devam eder)."""
    todo = [c for c in cells if c not in cache]
    for i, cid in enumerate(todo, 1):
        lat, lon = cells[cid]
        tr, en = reverse(lat, lon, "tr"), reverse(lat, lon, "en")
        cache[cid] = {"lat": round(lat, 4), "lon": round(lon, 4),
                      "tr": label(tr, fallback=en), "en": label(en)}
        if i % save_every == 0:
            save_cache(cache)
            print(f"  {i}/{len(todo)}")
    save_cache(cache)
    return len(todo)


def write_places(analog_dir: Path = ANALOG_DIR, cache: dict[str, dict] | None = None) -> int:
    """Analog dosyalarındaki place alanını önbellekten günceller (diğer alanlara dokunmaz)."""
    cache = load_cache() if cache is None else cache
    n = 0
    for path in sorted(analog_dir.glob("*.geojson")):
        fc = json.loads(path.read_text(encoding="utf-8"))
        for f in fc["features"]:
            f["properties"]["place"] = place_for(f["properties"]["id"], cache)
            n += f["properties"]["place"] is not None
        path.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="ağ isteği yapma, sadece önbelleği uygula")
    args = ap.parse_args()
    cache = load_cache()
    cells = analog_cells()
    if not args.offline:
        print(f"{len(cells)} kare, {sum(c not in cache for c in cells)} tanesi önbellekte yok")
        fetch_missing(cells, cache)
    print(f"yer adı yazılan aday: {write_places(cache=cache)} -> {ANALOG_DIR.relative_to(ROOT)}")
