"""pipeline/features.py: ee_export CSV'si -> grid.parquet dönüşümü (Earth Engine gerekmez)."""
import numpy as np
import pandas as pd
import pytest

from core.profiles import load_parameters
from pipeline.ee_export import RAW_COLUMNS
from pipeline.features import build_grid, haversine_km, to_levels

NODATA = -9999


def raw_row(lat, lon, **kw):
    row = dict(lon=lon, lat=lat, land_frac=1.0, slope_deg=3.0, roughness_m=20.0,
               lst_day_c=40.0, lst_night_c=10.0, ndvi=0.05, precip_mm=50.0, aod=0.3,
               aster_mi=1.0, aster_ci=1.005,  # yeni eşiklerle ikisi de 'baskın' (0,75)
               permafrost=0.0, access_min=120.0, pop_density=0.5,
               lc_12=0.0, lc_13=0.0, lc_15=0.0, lc_17=0.0)
    row.update(kw)
    return row


@pytest.fixture
def grid(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    rows = [
        raw_row(37.55, 29.68, lc_17=0.6),                    # Salda karesi: suyla maskelenmeli ama korunur
        raw_row(10.0, 10.0, lc_12=0.7),                      # tarım: maskeli
        raw_row(-20.0, 20.0, aod=NODATA, permafrost=NODATA), # veri boşluğu
        raw_row(78.0, -60.0, permafrost=0.8, ndvi=0.0, precip_mm=150),   # Earth Engine permafrost sütunu
        raw_row(0.0, 0.0),                                   # sıradan, uzak kare
        raw_row(-80.0, 100.0, lc_15=0.9),                  # Antarktika: MODIS kalıcı kar ve buz
        raw_row(5.0, 40.0, land_frac=0.2),                   # çoğu deniz kıyı karesi
        raw_row(29.16, -13.44, land_frac=0.3),               # Lanzarote: kıyı ama doğrulama karesi
    ]
    df = pd.DataFrame(rows)
    df.iloc[:3].to_csv(raw / "a.csv", index=False)
    df.iloc[2:].to_csv(raw / "b.csv", index=False)           # şerit sınırı tekrarı (satır 2)
    return build_grid(raw, tmp_path / "grid.parquet", cell_km=25, permafrost_files=[])


def test_columns_and_dedup(grid):
    assert len(grid) == 8
    assert set(load_parameters()) <= set(grid.columns)
    assert {"id", "name", "lat", "lon", "is_new", "masked", "known_id",
            "ops_road_access", "ops_remote"} <= set(grid.columns)


def test_masks_and_known_cells(grid):
    salda = grid[grid["known_id"] == "salda"].iloc[0]
    assert not salda["masked"] and not salda["is_new"]
    farm = grid[(grid["lat"] == 10.0)].iloc[0]
    assert farm["masked"] and farm["is_new"]


def test_nodata_and_percent(grid):
    gap = grid[grid["lat"] == -20.0].iloc[0]
    assert np.isnan(gap["dust_aod"])
    arctic = grid[grid["lat"] == 78.0].iloc[0]
    assert arctic["ground_ice"] == pytest.approx(0.8)
    assert arctic["aridity"] == pytest.approx(0.5 * (1 - 150 / 1000) + 0.5 * 1.0)


def test_derived_values(grid):
    row = grid[grid["lat"] == 0.0].iloc[0]
    assert row["surface_temp_c"] == pytest.approx(25)
    assert row["temp_range_c"] == pytest.approx(30)
    assert row["mafic_index"] == 0.75 and row["carbonate_index"] == 0.75
    assert bool(row["ops_road_access"]) and bool(row["ops_remote"])


def test_to_levels_edges():
    s = pd.Series([0.5, 1.00, 1.015, 2.0, np.nan])
    out = to_levels(s, [1.00, 1.01, 1.02, 1.03])
    assert list(out[:4]) == [0.0, 0.25, 0.5, 1.0] and np.isnan(out[4])


def test_haversine():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.2, abs=0.2)


def test_raw_columns_cover_features():
    assert {"slope_deg", "aster_ci", "permafrost", "access_min"} <= set(RAW_COLUMNS)


def test_ice_fallback_masks_antarctica(grid):
    ice = grid[grid["lat"] == -80.0].iloc[0]
    assert ice["masked"] and ice["masked_fraction"] == pytest.approx(0.9)


def test_low_land_fraction_masked_except_known(grid):
    assert grid[grid["lat"] == 5.0].iloc[0]["masked"]
    assert not grid[grid["known_id"] == "lanzarote"].iloc[0]["masked"]


def test_old_csv_without_new_columns(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    row = raw_row(0.0, 0.0)
    del row["lc_15"], row["land_frac"]
    pd.DataFrame([row]).to_csv(raw / "old.csv", index=False)
    g = build_grid(raw, tmp_path / "g.parquet", cell_km=25, permafrost_files=[])
    assert not g.iloc[0]["masked"]


def test_raw_columns_have_no_worldcover():
    assert not [c for c in RAW_COLUMNS if c.startswith("wc_")]  # maskeler MODIS lc_<sınıf> sütunlarından


def test_empty_tile_csv_is_skipped(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame([raw_row(0.0, 0.0)]).to_csv(raw / "dolu.csv", index=False)
    pd.DataFrame(columns=list(raw_row(0.0, 0.0))).to_csv(raw / "bos.csv", index=False)  # sadece başlık
    g = build_grid(raw, tmp_path / "g.parquet", cell_km=25, permafrost_files=[])
    assert len(g) == 1 and g["lat"].dtype.kind == "f"
