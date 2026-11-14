"""ESA CCI Permafrost (NetCDF) -> her ızgara karesi için donmuş zemin oranı (ground_ice, 0-1).

Earth Engine kataloğunda olmayan bu veri yerelde işlenir; Earth Engine'e yükleme gerekmez.

Dosya: data/raw/permafrost/*.nc (gitignore; CEDA'dan indirilir, DATA_SOURCES.md).
  Örn. ESACCI-PERMAFROST-L4-PFR-MODISLST_CRYOGRID-AREA4_PP-2023-fv05.0.nc
  PFR: permafrost alan oranı, YÜZDE (0-100), EPSG:4326, 0,01°, Kuzey Yarımküre 25°K-85°K.
  Boş (NaN) pikseller: deniz ya da permafrost olmayan kara -> 0 sayılır.

Yöntem:
  1. 0,01°'lik PFR, coarse_factor x coarse_factor bloklarla ortalanır (bellekte ~35 MB kalır).
  2. Toplamlı alan tablosu (integral image) ile her karenin kendi kapladığı enlem-boylam kutusunun
     ortalaması O(1)'de alınır. Kare boyu enleme göre: dx = km / (111,32 * cos(enlem)).
  3. Dosyanın kapsamadığı enlemlerdeki kareler 0 (permafrost yok; Güney Yarımküre sınırlılığı
     DATA_SOURCES.md'de yazılı).

Windows notu: netCDF kütüphanesi ASCII dışı karakter içeren yolları ("Masaüstü") açamaz;
böyle bir yolda dosya önce geçici klasöre kopyalanır.
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PERMAFROST_DIR = ROOT / "data" / "raw" / "permafrost"
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON_EQ = 111_320.0


@dataclass
class CoarseRaster:
    """Kuzeyden güneye değil, enlem artan sırada (dosyadaki gibi) bloklanmış oran rasterı."""
    lat0: float          # ilk satırın alt kenarı
    lon0: float          # ilk sütunun sol kenarı
    res: float           # derece
    frac: np.ndarray     # (satır, sütun), 0-1

    def integral(self) -> np.ndarray:
        s = np.zeros((self.frac.shape[0] + 1, self.frac.shape[1] + 1))
        s[1:, 1:] = self.frac.cumsum(0).cumsum(1)
        return s


def find_files(directory: Path = PERMAFROST_DIR) -> list[Path]:
    return sorted(directory.glob("*.nc")) if directory.exists() else []


def _ascii_path(path: Path) -> tuple[Path, Path | None]:
    if str(path).isascii():
        return path, None
    tmp = Path(tempfile.mkdtemp(prefix="geocosmos_pf_"))
    dst = tmp / "permafrost.nc"
    shutil.copyfile(path, dst)
    return dst, tmp


def load_coarse(path: Path, factor: int = 5, block_rows: int = 500, variable: str = "PFR") -> CoarseRaster:
    import xarray as xr

    readable, tmp = _ascii_path(path)
    try:
        with xr.open_dataset(readable) as ds:
            lat = ds["lat"].values.astype(float)
            lon = ds["lon"].values.astype(float)
            if lat[0] > lat[-1]:
                raise ValueError(f"{path.name}: enlem azalan sırada; bu biçim beklenmiyor")
            # float32 koordinatlarda komşu farkı yuvarlama hatası taşır; uçtan uca hesapla.
            res = round(float(lat[-1] - lat[0]) / (len(lat) - 1), 6)
            n_rows, n_cols = len(lat) // factor * factor, len(lon) // factor * factor
            var = ds[variable]
            out = np.empty((n_rows // factor, n_cols // factor), dtype=np.float32)
            step = block_rows // factor * factor
            for r in range(0, n_rows, step):
                blk = var.isel(time=0, lat=slice(r, min(r + step, n_rows)), lon=slice(0, n_cols)).values
                blk = np.nan_to_num(blk, nan=0.0) / 100.0  # yüzde -> oran; NaN = permafrost yok
                h = blk.shape[0] // factor
                out[r // factor:r // factor + h] = blk.reshape(h, factor, -1, factor).mean(axis=(1, 3))
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return CoarseRaster(lat0=round(float(lat[0]) - res / 2, 6), lon0=round(float(lon[0]) - res / 2, 6),
                        res=res * factor, frac=out)


def cell_fraction(raster: CoarseRaster, lat: np.ndarray, lon: np.ndarray, cell_km: float) -> np.ndarray:
    """Her karenin (merkez lat/lon, kenar cell_km) kutusundaki ortalama permafrost oranı."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    rows, cols = raster.frac.shape
    S = raster.integral()
    half_dy = cell_km * 1000 / M_PER_DEG_LAT / 2
    half_dx = cell_km * 1000 / (M_PER_DEG_LON_EQ * np.cos(np.radians(np.clip(lat, -89.9, 89.9)))) / 2
    half_dx = np.minimum(half_dx, 180.0)

    def idx(v, origin, n):
        return np.clip(np.round((v - origin) / raster.res).astype(int), 0, n)

    r0, r1 = idx(lat - half_dy, raster.lat0, rows), idx(lat + half_dy, raster.lat0, rows)
    r1 = np.maximum(r1, np.minimum(r0 + 1, rows))  # en az bir satır
    west, east = lon - half_dx, lon + half_dx
    total = np.zeros(len(lat))
    area = np.zeros(len(lat))
    # Tarih çizgisini aşan kutu, -360/+360 kaydırılmış parçalarıyla birlikte toplanır.
    for shift in (0, 360, -360):
        c0, c1 = idx(west + shift, raster.lon0, cols), idx(east + shift, raster.lon0, cols)
        ok = (c1 > c0) & (r1 > r0)
        total += np.where(ok, S[r1, c1] - S[r0, c1] - S[r1, c0] + S[r0, c0], 0.0)
        area += np.where(ok, (r1 - r0) * (c1 - c0), 0)
    frac = np.where(area > 0, total / np.maximum(area, 1), 0.0)
    # Dosya enlem kapsamı dışında: permafrost yok (0).
    lat_top = raster.lat0 + rows * raster.res
    outside = (lat + half_dy <= raster.lat0) | (lat - half_dy >= lat_top)
    return np.where(outside, 0.0, np.clip(frac, 0, 1))


def ground_ice_for(lat: np.ndarray, lon: np.ndarray, cell_km: float,
                   files: list[Path] | None = None, factor: int = 5) -> np.ndarray | None:
    """Yerel NetCDF dosyalarından ground_ice. Dosya yoksa None (çağıran Earth Engine sütununa düşer).
    Birden fazla dosya (ör. Kuzey Yarımküre + Antarktika) varsa her kare için en büyüğü alınır."""
    files = find_files() if files is None else files
    if not files:
        return None
    result = np.zeros(len(lat))
    for f in files:
        result = np.maximum(result, cell_fraction(load_coarse(f, factor), lat, lon, cell_km))
    return result
