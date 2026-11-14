"""pipeline/ uçtan uca: test ızgarası -> discovery, validation, heatmap, commentary, build.

Izgara sadece bu testte, elle kurulur; uygulamaya veri olarak girmez (ARCHITECTURE.md).
"""
import json

import numpy as np
import pandas as pd
import pytest

from core.profiles import load_known_analogs, load_profiles, load_targets
from pipeline import build as build_mod
from pipeline.commentary import add_comments, allowed_numbers, invented_numbers
from pipeline.features import compute_features
from tests.test_features import raw_row


@pytest.fixture(scope="module")
def grid():
    rng = np.random.default_rng(0)
    rows = [raw_row(a.lat, a.lon) for a in load_known_analogs().analogs]
    for _ in range(300):
        rows.append(raw_row(float(rng.uniform(-50, 80)), float(rng.uniform(-179, 179)),
                            slope_deg=float(rng.uniform(0, 30)), roughness_m=float(rng.uniform(0, 200)),
                            lst_day_c=float(rng.uniform(-30, 60)), lst_night_c=float(rng.uniform(-50, 20)),
                            ndvi=float(rng.uniform(0, 0.8)), precip_mm=float(rng.uniform(0, 2000)),
                            aod=float(rng.uniform(0, 1)), aster_mi=float(rng.uniform(0.95, 1.05)),
                            aster_ci=float(rng.uniform(0.98, 1.05)), permafrost=float(rng.uniform(0, 1)),
                            lc_13=float(rng.choice([0.0, 0.9], p=[0.9, 0.1]))))
    return compute_features(pd.DataFrame(rows), cell_km=25, permafrost_files=[])


def fake_gemini(prompt):
    return "Bu bölge düşük eğimli ve kurak; yerçekimi farkı ise kapanamaz."


@pytest.fixture(scope="module")
def built(grid, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("build")
    grid.to_parquet(tmp / "grid.parquet")
    report = build_mod.build(tmp / "grid.parquet", tmp / "out", fine_scan_path=tmp / "fine_scan.json",
                             generate=fake_gemini)
    return tmp, report


def test_all_files_written(built):
    tmp, report = built
    out = tmp / "out"
    n = len(load_targets()) * len(load_profiles())
    index = json.loads((out / "analogs" / "index.json").read_text(encoding="utf-8"))
    assert len(index) == n
    assert report["analogs"] == sum(1 for e in index if e["file"])
    for e in index:
        if e["file"]:
            fc = json.loads((out / "analogs" / e["file"]).read_text(encoding="utf-8"))
            assert 0 < len(fc["features"]) <= 20
    assert (out / "validation.json").exists() and (out / "targets.geojson").exists()
    assert json.loads((tmp / "fine_scan.json").read_text(encoding="utf-8"))


def test_analogs_spread_and_masked_excluded(built, grid):
    tmp, _ = built
    masked = set(grid.loc[grid["masked"], "id"])
    for f in (tmp / "out" / "analogs").glob("*.geojson"):
        feats = json.loads(f.read_text(encoding="utf-8"))["features"]
        ids = [x["properties"]["id"] for x in feats]
        assert not set(ids) & masked
        assert [x["properties"]["rank"] for x in feats] == list(range(1, len(feats) + 1))


def test_known_cells_named_with_past_tests(grid):
    from pipeline.discovery import run_discovery
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        run_discovery(grid, Path(d))
        props = [x["properties"] for f in Path(d).glob("*.geojson")
                 for x in json.loads(f.read_text(encoding="utf-8"))["features"]]
    known = [p for p in props if p["past_tests"]]
    for p in known:
        assert not p["is_new"] and "(" in p["name"]  # gerçek ad, koordinat değil


def test_validation_structure(built):
    tmp, _ = built
    v = json.loads((tmp / "out" / "validation.json").read_text(encoding="utf-8"))
    assert v["holdout_total"] == 4 and v["min_hits"] == 3
    statuses = {a["id"]: a["status"] for a in v["analogs"]}
    assert set(statuses) == {a.id for a in load_known_analogs().analogs}
    for a in v["analogs"]:
        if a["status"] == "ok":
            assert 0 < a["percentile"] <= 100 and a["target_id"] in a["targets"]


def test_heatmaps(built):
    from PIL import Image
    tmp, report = built
    meta = json.loads((tmp / "out" / "heatmaps" / "index.json").read_text(encoding="utf-8"))
    assert meta["crs"] == "EPSG:3857" and len(meta["files"]) == report["heatmaps"]
    img = np.array(Image.open(tmp / "out" / "heatmaps" / meta["files"][0]["file"]))
    assert img.shape[1] == 1440 and img.shape[2] == 4
    assert (img[..., 3] == 0).mean() > 0.5  # çoğu yer saydam (veri yok / maskeli)


def test_comments_written(built):
    tmp, report = built
    assert report["commentary"]["written"] > 0
    f = next((tmp / "out" / "analogs").glob("*.geojson"))
    first = json.loads(f.read_text(encoding="utf-8"))["features"][0]["properties"]
    assert first["ai_comment"].startswith("Bu bölge")


def test_invented_numbers_rejected(built, tmp_path):
    tmp, _ = built
    calls = []

    def liar(prompt):
        calls.append(1)
        return "Bu bölge Mars'a %97 benziyor ve 1971'de test edildi."

    analogs = tmp / "out" / "analogs"
    res = add_comments(analogs, generate=liar, cache_path=tmp_path / "c.json")
    assert res["written"] == 0 and res["empty"] > 0
    assert len(calls) >= 3  # ilk deneme + 2 yeniden deneme


def test_number_check_accepts_turkish_decimals():
    allowed = allowed_numbers({"a": 3.5, "b": [74.2, {"c": 100}]})
    assert invented_numbers("eğim 3,5° ve skor 74,2; tam 100", allowed) == []
    assert invented_numbers("skor 88", allowed) == ["88"]


def test_build_without_grid(tmp_path):
    report = build_mod.build(tmp_path / "yok.parquet", tmp_path / "out")
    assert report["grid"] == "yok" and (tmp_path / "out" / "targets.geojson").exists()


def test_meta_json_matches_config(built):
    tmp, _ = built
    meta = json.loads((tmp / "out" / "meta.json").read_text(encoding="utf-8"))
    assert [t["id"] for t in meta["tests"]] == list(load_profiles())
    assert set(meta["parameters"]) >= {"slope_deg", "carbonate_index"}
    assert set(meta["breakdown_notes"]) == {"moon", "mars"}
    assert meta["tests"][-1]["at_least"] == ["carbonate_index"]  # biyo-imza: Salda kararı


def test_scenario_names_known_cells(grid, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from api.main import app
    from api.routes import scenario as sc

    grid.to_parquet(tmp_path / "grid.parquet")
    monkeypatch.setattr(sc, "GRID_PATH", tmp_path / "grid.parquet")
    sc.load_grid.cache_clear()
    monkeypatch.setattr(sc.gemini, "translate", lambda t, p: {"weights": {"aridity": 1}, "unsupported": []})
    r = TestClient(app).post("/scenario", json={"text": "kurak", "target_id": "mars_gale"})
    sc.load_grid.cache_clear()
    assert r.status_code == 200
    analogs = r.json()["analogs"]
    assert analogs and all(a["test_id"] == "custom" for a in analogs)
    for a in analogs:
        if a["past_tests"]:
            assert "(" in a["name"]  # bilinen saha gerçek adıyla
