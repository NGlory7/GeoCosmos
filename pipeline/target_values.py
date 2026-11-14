"""Ay/Mars hedefleri için slope_deg ve roughness_m: Dünya kareleriyle AYNI kuralla.

Kural (config/grid.yaml > scale, pipeline/ee_export.py ile aynı):
  1. Yükseklik modeli hedef merkezli, her yönde metre ölçen bir projeksiyona (azimutal eşit uzaklık)
     500 m'lik kare piksellerle ortalanır. Kutupta da (Shackleton -89,9°) bozulmaz.
  2. slope_deg  = 4 komşulu eğim (derece); roughness_m = 11 x 11 piksellik (5,5 km) pencerede std.
  3. İkisinin de hedefi merkez alan 25 km x 25 km'lik karedeki ortalaması alınır.

Girdi: GDAL'ın okuyabildiği herhangi bir DEM (PDS .IMG etiketi, GeoTIFF). Önerilen ürünler:
  Mars: MOLA MEGDR 128 piksel/derece (PDS Geosciences Node, mgs-m-mola-5-megdr-l3-v1)
  Ay:   LOLA kutup LDEM'leri (Shackleton, Malapert), ekvator için LOLA LDEM 128 piksel/derece
DEM dosyaları büyük olduğu için repoya girmez: data/raw/dem/ altına koyun (gitignore).

Kullanım:
  python -m pipeline.target_values --target mars_jezero --dem data/raw/dem/megt00n090hb.lbl
Çıktı targets.yaml'a yapıştırılacak satırlardır; dosya otomatik değiştirilmez (yorumlar korunur).
"""
from __future__ import annotations

import argparse
import re

import numpy as np

from core.profiles import load_grid_config, load_targets


# --- Hesap (GDAL gerektirmez, test edilir) ------------------------------------------------

def slope_deg(dem: np.ndarray, pixel_m: float) -> np.ndarray:
    """4 komşulu merkezi farkla eğim (derece). Kenar pikselleri tek yönlü farkla hesaplanır."""
    dz_dy, dz_dx = np.gradient(dem.astype(float), pixel_m)
    return np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))


def roughness_m(dem: np.ndarray, radius_px: int) -> np.ndarray:
    """(2r+1) x (2r+1) penceredeki yükseklik standart sapması. Pencere taşan kenarlar NaN."""
    k = 2 * radius_px + 1
    out = np.full(dem.shape, np.nan)
    if min(dem.shape) < k:
        return out
    win = np.lib.stride_tricks.sliding_window_view(dem.astype(float), (k, k))
    out[radius_px:-radius_px or None, radius_px:-radius_px or None] = win.std(axis=(-2, -1))
    return out


def cell_means(dem: np.ndarray, pixel_m: float, cell_m: float, window_m: float) -> dict[str, float]:
    """dem: hedef merkezli, pixel_m'lik kare piksellerde yükseklik (m). Merkezdeki cell_m karenin ortalamaları."""
    radius_px = max(1, round(window_m / 2 / pixel_m))
    cell_px = round(cell_m / pixel_m)
    rows, cols = dem.shape
    need = cell_px + 2 * radius_px
    if rows < need or cols < need:
        raise ValueError(f"DEM penceresi küçük: {dem.shape}, en az {need} x {need} piksel gerekli")
    r0, c0 = (rows - cell_px) // 2, (cols - cell_px) // 2
    core = (slice(r0, r0 + cell_px), slice(c0, c0 + cell_px))
    return {
        "slope_deg": float(np.nanmean(slope_deg(dem, pixel_m)[core])),
        "roughness_m": float(np.nanmean(roughness_m(dem, radius_px)[core])),
    }


# --- DEM okuma (rasterio/GDAL) -----------------------------------------------------------

def _body_radius(proj4: str) -> str:
    """Kaynak DEM'in gök cismi küresi/elipsoidi: hedef projeksiyon AYNI cisim üzerinde kurulmalı,
    yoksa PROJ Dünya'ya göre datum dönüşümü dener."""
    r = re.search(r"\+R=([\d.]+)", proj4)
    if r:
        return f"+R={r.group(1)}"
    a, b = re.search(r"\+a=([\d.]+)", proj4), re.search(r"\+b=([\d.]+)", proj4)
    if a:
        return f"+a={a.group(1)} +b={(b or a).group(1)}"
    raise ValueError(f"DEM'in CRS'inde gök cismi yarıçapı yok: {proj4}")


def read_local_dem(path: str, lat: float, lon: float, pixel_m: float, half_m: float) -> np.ndarray:
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError(f"{path}: CRS yok (PDS ürünlerinde .lbl/.img etiketiyle açın)")
        dst_crs = CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} {_body_radius(src.crs.to_proj4())} "
                                 "+units=m +no_defs")
        n = int(round(2 * half_m / pixel_m))
        dst = np.full((n, n), np.nan, dtype="float64")
        reproject(
            source=rasterio.band(src, 1), destination=dst,
            dst_transform=from_origin(-half_m, half_m, pixel_m, pixel_m), dst_crs=dst_crs,
            dst_nodata=np.nan, resampling=Resampling.average,
        )
        scale = src.scales[0] if src.scales else 1.0
        offset = src.offsets[0] if src.offsets else 0.0
    if np.isnan(dst).mean() > 0.01:
        raise ValueError(f"{path}: hedef penceresinin %{np.isnan(dst).mean() * 100:.0f}'i boş; DEM bölgeyi kapsamıyor")
    return dst * scale + offset


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, help="config/targets.yaml içindeki id")
    ap.add_argument("--dem", required=True, help="DEM dosyası (GDAL'ın açabildiği)")
    ap.add_argument("--source", default=None, help="kartta görünecek kaynak adı (varsayılan: dosya adı)")
    args = ap.parse_args()

    target = load_targets()[args.target]
    cfg = load_grid_config()
    pixel_m = cfg["scale"]["dem_resample_m"]
    cell_m = cfg["grid"]["coarse_km"] * 1000
    window_m = cfg["scale"]["roughness_window_km"] * 1000
    half_m = cell_m / 2 + window_m / 2 + 2 * pixel_m
    dem = read_local_dem(args.dem, target.lat, target.lon, pixel_m, half_m)
    vals = cell_means(dem, pixel_m, cell_m, window_m)

    src = args.source or args.dem.replace("\\", "/").rsplit("/", 1)[-1]
    rule = f"{pixel_m:g} m, {cell_m / 1000:g} km kare (pipeline.target_values)"
    print(f"# {target.id} — config/targets.yaml > params içine yapıştırın")
    for key, v in vals.items():
        print(f'      {key}: {{ value: {v:.2f}, source: "{src} → {rule}" }}')


if __name__ == "__main__":
    main()
