"""Aday karelerin lojistik değerleri (Earth Engine) -> frontend/public/data/logistics.json.

Sadece analogs/*.geojson'daki kareler (hazır testlerin ilk 20'si; ~400 benzersiz kare) çekilir,
tüm Dünya değil. Dosyada zaten olan kare yeniden çekilmez. Puan ve yorum core/logistics.py'de,
ham değerlerden her çalıştırmada yeniden hesaplanır (eşik değişince yeniden çekmek gerekmez).

Kaynaklar (config/grid.yaml > logistics.sources):
  MAP erişim süresi 2015 · WRI Global Power Plant Database · JRC Global Surface Water 1.4 ·
  SEDAC GPW v4.11 nüfus sayısı 2020 · Copernicus DEM GLO-30

Kullanım:
  python -m pipeline.logistics            # eksik kareleri çek, puanları yaz
  python -m pipeline.logistics --offline  # Earth Engine'e bağlanma, sadece puanları yeniden hesapla
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from core import logistics as core
from core.profiles import load_grid_config

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "frontend" / "public" / "data" / "logistics.json"
ANALOG_DIR = ROOT / "frontend" / "public" / "data" / "analogs"
BATCH = 50


def cells_in(analog_dir: Path) -> dict[str, tuple[float, float]]:
    cells = {}
    for path in sorted(analog_dir.glob("*.geojson")):
        for f in json.loads(path.read_text(encoding="utf-8"))["features"]:
            p = f["properties"]
            cells[p["id"]] = (p["lat"], p["lon"])
    return cells


def _none_if_nodata(v):
    return None if v is None or (isinstance(v, float) and v != v) else v


def fetch(cells: dict[str, tuple[float, float]], cfg: dict) -> dict[str, dict]:
    """Earth Engine'den ham değerler; dönüş {id: raw} (core/logistics.py > modül notu)."""
    import ee

    src = cfg["sources"]
    pts = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lon, lat]), {"id": cid}) for cid, (lat, lon) in cells.items()])
    cell = pts.map(lambda f: f.buffer(cfg["cell_radius_km"] * 1000))
    region = pts.map(lambda f: f.buffer(cfg["region_radius_km"] * 1000))

    def by_id(fc, prop):
        return {f["properties"]["id"]: f["properties"].get(prop) for f in fc.getInfo()["features"]}

    # Erişim: karenin en erişilebilir noktası (üs oraya kurulur)
    access = ee.Image(src["access"]).select("accessibility")
    access_min = by_id(access.reduceRegions(cell, ee.Reducer.min(), scale=1000, tileScale=4), "min")

    # Yükseklik: kare ortalaması
    dem = ee.ImageCollection(src["dem"]).select("DEM").mosaic()
    elev = by_id(dem.reduceRegions(cell, ee.Reducer.mean(), scale=500, tileScale=4), "mean")

    # Nüfus: bölge yarıçapında toplam
    pop = (ee.ImageCollection(src["population"]).filter(ee.Filter.calendarRange(2020, 2020, "year")).first()
           .select("population_count"))
    pop_region = by_id(pop.reduceRegions(region, ee.Reducer.sum(), scale=1000, tileScale=4), "sum")

    # Kalıcı su: 1 km'ye kaba (herhangi bir 30 m su pikseli = su). Mesafe her nokta için jeodezik
    # (FeatureCollection.distance): derece ızgarasında piksel sayımı yüksek enlemde doğu-batıyı şişirirdi.
    occ = ee.Image(src["water"]).select("occurrence").gte(cfg["water_min_occurrence"]).selfMask()
    water1k = occ.reduceResolution(ee.Reducer.max(), maxPixels=4096).reproject(crs="EPSG:4326", scale=1000)
    search_m = cfg["water_search_km"] * 1000

    def nearest_water(f):
        d = ee.FeatureCollection([f]).distance(search_m, 100).updateMask(water1k)
        v = d.reduceRegion(ee.Reducer.min(), f.geometry().buffer(search_m), scale=1000, tileScale=4, maxPixels=1e9)
        return f.set("water_m", v.get("distance"))

    water_m = by_id(pts.map(nearest_water), "water_m")

    # En yakın santral (ve bölgedeki toplam kapasite)
    plants = ee.FeatureCollection(src["plants"])
    flt = ee.Filter.withinDistance(distance=cfg["plant_search_km"] * 1000, leftField=".geo", rightField=".geo", maxError=1000)
    joined = ee.Join.saveBest(matchKey="plant", measureKey="join_m").apply(pts, plants, flt)
    nearest = {}  # eşleşmesi olmayan nokta join'de düşer: arama yarıçapında santral yok
    for f in joined.map(lambda f: ee.Feature(None, {
        # join_m bu filtreyle dolmuyor: mesafe jeodezik olarak ayrıca ölçülür
        "id": f.get("id"), "dist_m": f.geometry().distance(ee.Feature(f.get("plant")).geometry(), 10),
        "name": ee.Feature(f.get("plant")).get("name"), "fuel": ee.Feature(f.get("plant")).get("fuel1"),
        "mw": ee.Feature(f.get("plant")).get("capacitymw"), "country": ee.Feature(f.get("plant")).get("country_lg"),
    })).getInfo()["features"]:
        nearest[f["properties"]["id"]] = f["properties"]
    mw_region = by_id(region.map(lambda f: f.set("mw", plants.filterBounds(f.geometry()).aggregate_sum("capacitymw"))), "mw")

    out = {}
    for cid, (lat, lon) in cells.items():
        n = nearest.get(cid)
        w = _none_if_nodata(water_m.get(cid))
        out[cid] = {
            "lat": round(lat, 4), "lon": round(lon, 4),
            "access_min": _none_if_nodata(access_min.get(cid)),
            "elev_m": _none_if_nodata(elev.get(cid)),
            "pop_region": _none_if_nodata(pop_region.get(cid)),
            "water_km": None if w is None else round(w / 1000, 1),
            "water_none": w is None,
            "plant_km": None if n is None else round(n["dist_m"] / 1000, 1),
            "plant_none": n is None,
            "plant": None if n is None else {k: n.get(k) for k in ("name", "fuel", "mw", "country")},
            "plant_mw_region": _none_if_nodata(mw_region.get(cid)),
        }
        for k in ("access_min", "elev_m", "pop_region", "plant_mw_region"):
            if out[cid][k] is not None:
                out[cid][k] = round(out[cid][k], 1)
    return out


def write(raw: dict[str, dict], cfg: dict, out_path: Path = OUT_PATH) -> Path:
    cells = {cid: {"raw": r, **core.score(r, cfg)} for cid, r in sorted(raw.items())}
    doc = {
        "labels": {k: cfg["scores"][k]["label"] for k in core.KEYS},
        "sources": cfg["sources"],
        "note": "Benzerliğe katılmaz. Her kalem config/grid.yaml > logistics eşikleriyle 0-100 (logaritmik); toplam = mevcut kalemlerin ortalaması.",
        "cells": cells,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return out_path


def load_raw(out_path: Path = OUT_PATH) -> dict[str, dict]:
    try:
        return {cid: c["raw"] for cid, c in json.loads(out_path.read_text(encoding="utf-8"))["cells"].items()}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {}


def run(analog_dir: Path = ANALOG_DIR, out_path: Path = OUT_PATH, online: bool = True) -> dict:
    """Eksik kareleri çeker (online ve EE_PROJECT varsa), tüm puanları yeniden yazar.
    Dönüş: {"cells": n, "fetched": n, "missing": n, "skipped": sebep|None}."""
    cfg = load_grid_config()["logistics"]
    raw = load_raw(out_path)
    todo = {cid: ll for cid, ll in cells_in(analog_dir).items() if cid not in raw}
    skipped, fetched = None, 0
    if todo and online:
        load_dotenv(ROOT / ".env")
        try:
            import ee
            ee.Initialize(project=os.environ["EE_PROJECT"])
        except Exception as e:  # anahtar/kimlik yok (CI): mevcut değerlerle devam
            skipped = f"Earth Engine yok: {type(e).__name__}"
        else:
            items = list(todo.items())
            for i in range(0, len(items), BATCH):
                part = fetch(dict(items[i:i + BATCH]), cfg)
                raw.update(part)
                fetched += len(part)
                write(raw, cfg, out_path)  # yarıda kesilirse çekilenler kalsın
                print(f"lojistik: {min(i + BATCH, len(items))}/{len(items)} kare", flush=True)
    elif todo:
        skipped = "çevrimdışı"
    if raw or out_path.exists():
        write(raw, cfg, out_path)
    return {"cells": len(raw), "fetched": fetched, "missing": len(todo) - fetched, "skipped": skipped}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true")
    print(run(online=not ap.parse_args().offline))
