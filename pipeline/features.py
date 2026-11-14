"""data/raw/*.csv (pipeline/ee_export.py çıktısı) -> data/processed/grid.parquet.

Ham ölçümleri config/test_profiles.yaml > parameters'taki parametrelere çevirir.
Kurallar config/grid.yaml'dan okunur (core.profiles.load_grid_config):

- slope_deg, roughness_m: Earth Engine'de 500 m DEM'den hesaplanmış olarak gelir.
- surface_temp_c = (gündüz + gece) / 2, temp_range_c = gündüz - gece (MODIS LST).
- aridity: indices.aridity formülü (IMERG yağış + MODIS NDVI).
- mafic_index, carbonate_index: ASTER oranı -> indices.<param>.breaks ile 0-1 sıralı ölçek.
- ground_ice: ESA CCI Permafrost oranı (0-1). data/raw/permafrost/*.nc varsa yerelde hesaplanır
  (pipeline/permafrost.py, Earth Engine'e yükleme gerekmez); yoksa Earth Engine asset sütunu kullanılır.
- masked: (1) masks.landcover.classes (MODIS MCD12Q1: tarım, yerleşim, kar/buz, su) oranı
  masks.max_masked_fraction'ı geçen kareler;
  (2) kara oranı masks.min_land_fraction'ın altındaki kıyı/ada kareleri. Satırlar
  silinmez, sadece işaretlenir: doğrulamanın yüzdelik paydası için gerekir. Doğrulama yerlerinin
  kendi kareleri hiçbir zaman maskelenmez (masks.never_mask_known_analogs).
- is_new: bilinen tüm sahalara (doğrulama seti + exclude_only) exclude_radius_km'den uzak kare.
- ops_road_access, ops_remote: ops_tags eşikleri.

Kullanım:  python -m pipeline.features   (data/raw/*.csv -> data/processed/grid.parquet)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from core.geo import haversine_km
from core.profiles import load_grid_config, load_known_analogs, load_parameters
from pipeline import permafrost

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
GRID_PATH = ROOT / "data" / "processed" / "grid.parquet"
LEVELS = np.array([0.0, 0.25, 0.5, 0.75, 1.0])


def read_raw(raw_dir: Path = RAW_DIR, nodata: float | None = None) -> pd.DataFrame:
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"{raw_dir} içinde CSV yok. Önce: python -m pipeline.ee_export")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    nodata = load_grid_config()["export"]["nodata"] if nodata is None else nodata
    df = df.replace(nodata, np.nan)
    # Şerit sınırında aynı kare iki dosyada çıkabilir.
    return df.drop_duplicates(subset=["lon", "lat"]).reset_index(drop=True)


def to_levels(values: pd.Series, breaks: list[float]) -> pd.Series:
    """İndeks değerini 0 / 0.25 / 0.5 / 0.75 / 1 basamağına çevirir (DATA_SOURCES.md > 0-1 sıralı ölçek)."""
    idx = np.searchsorted(np.asarray(breaks), values.to_numpy(dtype=float), side="right")
    out = LEVELS[np.clip(idx, 0, 4)]
    return pd.Series(np.where(values.isna(), np.nan, out), index=values.index)


def aridity(precip_mm: pd.Series, ndvi: pd.Series, cfg: dict) -> pd.Series:
    dry_p = (1 - precip_mm / cfg["precip_wet_mm"]).clip(0, 1)
    dry_v = (1 - ndvi / cfg["ndvi_dense"]).clip(0, 1)
    return cfg["w_precip"] * dry_p + cfg["w_ndvi"] * dry_v


def cell_name(lat: float, lon: float) -> str:
    return f"{abs(lat):.2f}°{'K' if lat >= 0 else 'G'}, {abs(lon):.2f}°{'D' if lon >= 0 else 'B'}"


def compute_features(raw: pd.DataFrame, cell_km: float, permafrost_files: list[Path] | None = None) -> pd.DataFrame:
    """permafrost_files: None ise data/raw/permafrost/*.nc aranır; [] verilirse yerel dosya kullanılmaz."""
    cfg = load_grid_config()
    ind = cfg["indices"]
    vs = load_known_analogs()

    g = pd.DataFrame({
        "id": [f"g{cell_km:g}_{la:.3f}_{lo:.3f}" for la, lo in zip(raw["lat"], raw["lon"])],
        "name": [cell_name(la, lo) for la, lo in zip(raw["lat"], raw["lon"])],
        "lat": raw["lat"], "lon": raw["lon"],
        "slope_deg": raw["slope_deg"],
        "roughness_m": raw["roughness_m"],
        "surface_temp_c": (raw["lst_day_c"] + raw["lst_night_c"]) / 2,
        "temp_range_c": raw["lst_day_c"] - raw["lst_night_c"],
        "aridity": aridity(raw["precip_mm"], raw["ndvi"], ind["aridity"]),
        "dust_aod": raw["aod"],
        "mafic_index": to_levels(raw["aster_mi"], ind["mafic_index"]["breaks"]),
        "carbonate_index": to_levels(raw["aster_ci"], ind["carbonate_index"]["breaks"]),
    })
    local = permafrost.ground_ice_for(g["lat"].to_numpy(), g["lon"].to_numpy(), cell_km,
                                      files=permafrost_files)
    if local is not None:
        g["ground_ice"] = local
    else:
        pf = raw["permafrost"] if "permafrost" in raw else pd.Series(np.nan, index=raw.index)
        g["ground_ice"] = pf.clip(0, 1)  # ee_export yüzdeyi zaten 100'e böler

    # Maske: WorldCover sınıf oranları
    lc_cols = [f"lc_{c}" for c in cfg["masks"]["landcover"]["classes"] if f"lc_{c}" in raw]
    g["masked_fraction"] = raw[lc_cols].fillna(0).sum(axis=1).clip(0, 1) if lc_cols else 0.0
    g["land_frac"] = raw["land_frac"] if "land_frac" in raw else 1.0

    # Bilinen sahalara uzaklık -> is_new; doğrulama yerlerinin kendi kareleri -> known_id
    lat, lon = g["lat"].to_numpy(), g["lon"].to_numpy()
    min_dist = np.full(len(g), np.inf)
    for site in vs.all_known_sites():
        min_dist = np.minimum(min_dist, haversine_km(lat, lon, site.lat, site.lon))
    g["is_new"] = min_dist > vs.exclude_radius_km

    g["known_id"] = pd.Series([None] * len(g), dtype=object)
    for a in vs.analogs:
        d = haversine_km(lat, lon, a.lat, a.lon)
        i = int(np.argmin(d))
        if d[i] <= cell_km:  # koordinatı içeren kare (köşegen payıyla)
            g.loc[i, "known_id"] = a.id

    never_mask = cfg["masks"].get("never_mask_known_analogs", True)
    g["masked"] = ((g["masked_fraction"] > cfg["masks"]["max_masked_fraction"])
                   | (g["land_frac"] < cfg["masks"].get("min_land_fraction", 0.0)))
    if never_mask:
        g.loc[g["known_id"].notna(), "masked"] = False

    # Operasyon etiketleri (puan değil)
    ops = cfg["ops_tags"]
    g["ops_road_access"] = (raw["access_min"] < ops["road_access"]["max_minutes"]).where(raw["access_min"].notna())
    g["ops_remote"] = (raw["pop_density"] < ops["remote"]["max_density"]).where(raw["pop_density"].notna())

    missing = set(load_parameters()) - set(g.columns)
    if missing:
        raise RuntimeError(f"features.py şu parametreleri üretmiyor: {sorted(missing)}")
    return g


def build_grid(raw_dir: Path = RAW_DIR, out: Path = GRID_PATH, cell_km: float | None = None,
               permafrost_files: list[Path] | None = None) -> pd.DataFrame:
    cell_km = cell_km or load_grid_config()["grid"]["coarse_km"]
    g = compute_features(read_raw(raw_dir), cell_km, permafrost_files)
    out.parent.mkdir(parents=True, exist_ok=True)
    g.to_parquet(out, index=False)
    return g


def summary(g: pd.DataFrame) -> str:
    params = list(load_parameters())
    cover = (g[params].notna().mean() * 100).round(1)
    lines = [f"{len(g)} kare, {int(g['masked'].sum())} maskeli, {int(g['is_new'].sum())} yeni aday olabilir",
             f"doğrulama kareleri: {sorted(g['known_id'].dropna())}",
             "veri kapsamı (%): " + ", ".join(f"{k}={v}" for k, v in cover.items())]
    return "\n".join(lines)


if __name__ == "__main__":
    grid = build_grid()
    print("yazıldı:", GRID_PATH.relative_to(ROOT))
    print(summary(grid))
