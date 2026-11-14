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
  python -m pipeline.target_values --all                      # 6 hedef, PDS'ten uzaktan (indirme yok)
  python -m pipeline.target_values --target mars_jezero       # tek hedef, PDS'ten uzaktan
  python -m pipeline.target_values --target mars_jezero --dem data/raw/dem/megt44n000hb.lbl
Çıktı targets.yaml'a yapıştırılacak satırlardır; dosya otomatik değiştirilmez (yorumlar korunur).

Uzaktan okuma: --dem verilmezse PDS_DEMS'teki ürün GDAL /vsicurl/ ile açılır; GDAL sadece hedefin
çevresindeki baytları HTTP aralık isteğiyle çeker (hedef başına birkaç MB, 5-30 sn).
Windows notu: curl, ASCII dışı yoldaki ("Masaüstü") sertifika dosyasını açamaz; sertifika
paketi geçici bir ASCII yola kopyalanır (_ascii_ca_bundle).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile

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


# --- Hedef başına PDS ürünü --------------------------------------------------------------
# Hepsi PDS Geosciences Node (challenge kaynak listesi: NASA PDS, NASA LRO).
_MOLA = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/"
_LOLA = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/"
PDS_DEMS: dict[str, tuple[str, str]] = {
    "mars_jezero": (_MOLA + "megt44n000hb.lbl", "MOLA MEGDR 128 piksel/derece (PDS, megt44n000hb)"),
    "mars_gale": (_MOLA + "megt00n090hb.lbl", "MOLA MEGDR 128 piksel/derece (PDS, megt00n090hb)"),
    "mars_arcadia": (_MOLA + "megt88n180hb.lbl", "MOLA MEGDR 128 piksel/derece (PDS, megt88n180hb)"),
    "moon_shackleton": (_LOLA + "polar/img/ldem_80s_80m.lbl", "LOLA LDEM 80S 80 m (PDS, ldem_80s_80m)"),
    "moon_malapert": (_LOLA + "polar/img/ldem_80s_80m.lbl", "LOLA LDEM 80S 80 m (PDS, ldem_80s_80m)"),
    "moon_marius_hills": (_LOLA + "cylindrical/img/ldem_128.lbl", "LOLA LDEM 128 piksel/derece (PDS, ldem_128)"),
}


def _ascii_ca_bundle() -> None:
    """rasterio import edilmeden ÖNCE çağrılır: sertifika paketi ASCII dışı yoldaysa kopyalanır."""
    if os.environ.get("GDAL_CURL_CA_BUNDLE"):
        return
    try:
        import certifi
    except ImportError:
        return
    ca = certifi.where()
    if not ca.isascii():
        dst = os.path.join(tempfile.gettempdir(), "geocosmos_cacert.pem")
        shutil.copyfile(ca, dst)
        ca = dst
    os.environ.setdefault("GDAL_CURL_CA_BUNDLE", ca)
    os.environ.setdefault("CURL_CA_BUNDLE", ca)
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("GDAL_HTTP_TIMEOUT", "120")


def remote(url: str) -> str:
    return "/vsicurl/" + url


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
    _ascii_ca_bundle()
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


def values_for(target_id: str, dem: str | None = None) -> tuple[dict[str, float], str]:
    """(değerler, kaynak) — dem verilmezse PDS_DEMS'teki ürün uzaktan okunur."""
    target = load_targets()[target_id]
    cfg = load_grid_config()
    pixel_m = cfg["scale"]["dem_resample_m"]
    cell_m = cfg["grid"]["coarse_km"] * 1000
    window_m = cfg["scale"]["roughness_window_km"] * 1000
    half_m = cell_m / 2 + window_m / 2 + 2 * pixel_m
    if dem is None:
        if target_id not in PDS_DEMS:
            raise SystemExit(f"{target_id} için PDS ürünü tanımlı değil; --dem verin")
        url, src = PDS_DEMS[target_id]
        dem = remote(url)
    else:
        src = dem.replace("\\", "/").rsplit("/", 1)[-1]
    vals = cell_means(read_local_dem(dem, target.lat, target.lon, pixel_m, half_m), pixel_m, cell_m, window_m)
    rule = f"{pixel_m:g} m, {cell_m / 1000:g} km kare (pipeline.target_values)"
    return vals, f"{src} → {rule}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", help="config/targets.yaml içindeki id")
    ap.add_argument("--all", action="store_true", help="PDS_DEMS'teki tüm hedefler")
    ap.add_argument("--dem", default=None, help="yerel DEM dosyası (verilmezse PDS'ten uzaktan)")
    ap.add_argument("--source", default=None, help="kartta görünecek kaynak adı")
    args = ap.parse_args()
    if not args.all and not args.target:
        ap.error("--target ya da --all gerekli")
    for tid in (PDS_DEMS if args.all else [args.target]):
        vals, src = values_for(tid, args.dem if not args.all else None)
        print(f"# {tid} — config/targets.yaml > params içine yapıştırın")
        for key, v in vals.items():
            print(f'      {key}: {{ value: {v:.2f}, source: "{args.source or src}" }}')


if __name__ == "__main__":
    main()
