"""Dünya geneli benzerlik ısı haritası -> frontend/public/data/heatmaps/<hedef>_<test>.png + index.json.

PNG, Web Mercator (EPSG:3857) satırlarıyla çizilir: Leaflet ImageOverlay görüntüyü haritanın
kendi (Mercator) koordinatlarında doğrusal gerer, bu yüzden düz enlem-boylam (equirectangular)
bir PNG kuzeyde/güneyde kayardı. Sınırlar index.json'da: [[güney, batı], [kuzey, doğu]].

- Her kare kendi gerçek boyunda (dx = km / (111,32 * cos(enlem))) boyanır.
- Maskeli kareler ve veri olmayan yerler tamamen saydamdır.
- Renk 0-100 mutlak skordur: dosyalar arası karşılaştırılabilir.

Kullanım:  python -m pipeline.heatmap
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from core.profiles import load_grid_config, load_parameters, load_profiles, load_targets
from core.scoring import score_grid, usable_weights

ROOT = Path(__file__).resolve().parent.parent
GRID_PATH = ROOT / "data" / "processed" / "grid.parquet"
OUT_DIR = ROOT / "frontend" / "public" / "data" / "heatmaps"
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON_EQ = 111_320.0


def merc_y(lat):
    lat = np.radians(np.clip(lat, -85.05, 85.05))
    return np.log(np.tan(np.pi / 4 + lat / 2))


def rasterize(grid: pd.DataFrame, values: np.ndarray, cell_km: float, width: int,
              lat_range: tuple[float, float]) -> np.ndarray:
    """Kare değerlerini (NaN = saydam) Web Mercator rastera boyar. Dönüş: (H, W), NaN boş."""
    south, north = lat_range
    y_top, y_bot = merc_y(north), merc_y(south)
    height = int(round(width * (y_top - y_bot) / (2 * math.pi)))
    img = np.full((height, width), np.nan, dtype=np.float32)
    lat = grid["lat"].to_numpy(float)
    lon = grid["lon"].to_numpy(float)
    half_dy = cell_km * 1000 / M_PER_DEG_LAT / 2
    half_dx = cell_km * 1000 / (M_PER_DEG_LON_EQ * np.cos(np.radians(np.clip(lat, -89, 89)))) / 2
    px = width / 360.0
    py = height / (y_top - y_bot)
    c0 = np.floor((lon - half_dx + 180) * px).astype(int)
    c1 = np.ceil((lon + half_dx + 180) * px).astype(int)
    r0 = np.floor((y_top - merc_y(lat + half_dy)) * py).astype(int)
    r1 = np.ceil((y_top - merc_y(lat - half_dy)) * py).astype(int)
    order = np.argsort(values)  # yüksek skor en son boyanır (üstte kalır)
    for i in order:
        v = values[i]
        if np.isnan(v):
            continue
        a, b = max(r0[i], 0), min(max(r1[i], r0[i] + 1), height)
        for c_lo, c_hi in ((c0[i], c1[i]), (c0[i] + width, c1[i] + width), (c0[i] - width, c1[i] - width)):
            lo, hi = max(c_lo, 0), min(max(c_hi, c_lo + 1), width)
            if lo < hi and a < b:
                img[a:b, lo:hi] = v
    return img


def to_rgba(img: np.ndarray, colormap: str, alpha: float) -> np.ndarray:
    from matplotlib import colormaps
    rgba = colormaps[colormap](np.nan_to_num(img / 100.0, nan=0.0))
    rgba[..., 3] = np.where(np.isnan(img), 0.0, alpha)
    return (rgba * 255).astype(np.uint8)


def run_heatmaps(grid: pd.DataFrame | None = None, out_dir: Path = OUT_DIR) -> list[dict]:
    from matplotlib import pyplot as plt

    grid = pd.read_parquet(GRID_PATH) if grid is None else grid
    cfg = load_grid_config()
    hm, cell_km = cfg["heatmap"], cfg["grid"]["coarse_km"]
    params = load_parameters()
    visible = ~grid["masked"].to_numpy(bool) if "masked" in grid else np.ones(len(grid), bool)
    out_dir.mkdir(parents=True, exist_ok=True)
    south, north = hm["lat_range"]
    index = []
    for target in load_targets().values():
        for profile in load_profiles().values():
            if not usable_weights(profile.weights, target, params):
                continue
            scores = score_grid(grid, target, profile.weights, params,
                                profile.at_least)["score_total"].to_numpy(float)
            img = rasterize(grid, np.where(visible, scores, np.nan), cell_km, hm["width_px"], (south, north))
            name = f"{target.id}_{profile.id}.png"
            plt.imsave(out_dir / name, to_rgba(img, hm["colormap"], hm["alpha"]))
            index.append({"target_id": target.id, "test_id": profile.id, "file": name})
    meta = {"crs": "EPSG:3857", "bounds": [[south, -180], [north, 180]],
            "value": "score_total", "vmin": 0, "vmax": 100, "colormap": hm["colormap"],
            "files": index}
    (out_dir / "index.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    keep = {e["file"] for e in index}
    for old in out_dir.glob("*.png"):
        if old.name not in keep:
            old.unlink()
    return index


if __name__ == "__main__":
    print(f"{len(run_heatmaps())} ısı haritası -> {OUT_DIR.relative_to(ROOT)}")
