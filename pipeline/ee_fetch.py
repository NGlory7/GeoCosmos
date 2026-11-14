"""Hızlı yol: karoları Earth Engine'den interaktif (paralel) çekip doğrudan data/raw/*.csv yazar.

Neden: ticari olmayan projelerde toplu export görevleri aynı anda sadece 2 tane çalışır; 470
karo 6-12 saat sürer. İnteraktif sorgular (yüksek hacimli uç nokta) paralel çalışabilir; bir karo
70-130 sn sürüyor ve 5 dk / 5000 satır sınırının altında kalıyor. 10 paralel işle ~1-1,5 saat.

- ee_export.py ile AYNI görüntü (build_image), aynı karolar (regions + land_regions), aynı sütunlar.
- Dosya adı = karo adı: toplu exporttan inen dosyayla aynı ad; zaten olan karo atlanır (devam eder).
- Hata: 3 deneme; zaman aşımı ya da "too large" olursa karo boylamda ikiye bölünür (_a, _b).

Kullanım:
  python -m pipeline.ee_fetch                # tüm kara karoları, 10 paralel iş
  python -m pipeline.ee_fetch --workers 6
  python -m pipeline.ee_fetch --bbox -112 37 -109 40     # bölgesel
"""
from __future__ import annotations

import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from core.profiles import load_grid_config
from pipeline.ee_export import RAW_COLUMNS, _ee, _sample, build_image, center_lat, land_regions, regions

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
HIGH_VOLUME = "https://earthengine-highvolume.googleapis.com"
SPLIT_ERRORS = ("timed out", "too large", "Too many", "memory", "Computation timed out", "exceeds")


def init() -> None:
    load_dotenv(ROOT / ".env")
    project = os.getenv("EE_PROJECT")
    if not project:
        raise SystemExit(".env > EE_PROJECT tanımlı değil")
    _ee().Initialize(project=project, opt_url=HIGH_VOLUME)


def columns() -> list[str]:
    return RAW_COLUMNS + [f"lc_{c}" for c in load_grid_config()["masks"]["landcover"]["classes"]]


def fetch_tile(name: str, box: tuple[float, float, float, float], cell_km: float) -> pd.DataFrame:
    ee = _ee()
    x0, y0, x1, y1 = box
    image, proj = build_image(cell_km, center_lat(y0, y1))
    feats = _sample(image, proj, ee.Geometry.Rectangle([x0, y0, x1, y1], None, False)).getInfo()["features"]
    cols = columns()
    return pd.DataFrame([{c: f["properties"].get(c) for c in cols} for f in feats], columns=cols)


def fetch_with_retry(name, box, cell_km, out_dir: Path, depth: int = 0) -> list[str]:
    """Karoyu yazar; gerekirse ikiye bölerek. Dönüş: yazılan dosya adları."""
    last = None
    for attempt in range(3):
        try:
            df = fetch_tile(name, box, cell_km)
            tmp = out_dir / f"{name}.csv.part"
            df.to_csv(tmp, index=False)
            tmp.replace(out_dir / f"{name}.csv")
            return [name]
        except Exception as e:  # ağ, kota, zaman aşımı
            last = str(e)
            if any(k.lower() in last.lower() for k in SPLIT_ERRORS) and depth < 3:
                break
            time.sleep(10 * (attempt + 1))
    if depth < 3 and last and any(k.lower() in last.lower() for k in SPLIT_ERRORS):
        x0, y0, x1, y1 = box
        xm = round((x0 + x1) / 2, 4)
        return (fetch_with_retry(f"{name}_a", (x0, y0, xm, y1), cell_km, out_dir, depth + 1)
                + fetch_with_retry(f"{name}_b", (xm, y0, x1, y1), cell_km, out_dir, depth + 1))
    raise RuntimeError(f"{name}: {last}")


def is_done(name: str, files: set[str], depth: int = 0) -> bool:
    """Karonun dosyası var mı; ya da ikiye bölünmüş parçalarının (_a, _b) ikisi de tamam mı."""
    if name in files:
        return True
    return depth < 3 and is_done(f"{name}_a", files, depth + 1) and is_done(f"{name}_b", files, depth + 1)


def done_names(out_dir: Path, names: list[str]) -> set[str]:
    files = {p.stem for p in out_dir.glob("*.csv")}
    return {n for n in names if is_done(n, files)}


def run(cell_km: float, bbox=None, workers: int = 10, out_dir: Path = RAW_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    planned = regions(cell_km, bbox)
    done = done_names(out_dir, [n for n, _ in planned])
    todo = [(n, r) for n, r in planned if n not in done]
    todo = land_regions(todo) if todo else []
    print(f"{len(todo)} karo çekilecek ({len(done)} dosya zaten var), {workers} paralel iş", flush=True)
    t0, ok, failed = time.time(), 0, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fetch_with_retry, n, r, cell_km, out_dir): n for n, r in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                fut.result()
                ok += 1
            except Exception as e:
                failed.append(futs[fut])
                print("HATA", e, flush=True)
            if i % 10 == 0 or i == len(todo):
                el = time.time() - t0
                eta = el / i * (len(todo) - i)
                print(f"{i}/{len(todo)} karo · {el / 60:.0f} dk geçti · kalan ~{eta / 60:.0f} dk", flush=True)
    print(f"bitti: {ok} karo, {len(failed)} hata {failed[:10]}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell-km", type=float, default=None)
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()
    init()
    run(args.cell_km or load_grid_config()["grid"]["coarse_km"], tuple(args.bbox) if args.bbox else None, args.workers)


if __name__ == "__main__":
    main()
