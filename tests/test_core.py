"""core/ birim testleri: config dosyaları geçerli mi, motor doğru sıralıyor mu?"""
import math

import pandas as pd
import pytest

from core.profiles import load_parameters, load_profiles, load_targets, normalize_weights
from core.schemas import TEST_IDS, SourcedValue, Target
from core.scoring import score_grid, top_analogs


def test_config_loads():
    profiles = load_profiles()
    assert set(profiles) == set(TEST_IDS)
    for p in profiles.values():
        assert math.isclose(sum(p.weights.values()), 1.0)
    assert len(load_targets()) == 6


def test_normalize_drops_unknown_and_nonpositive():
    w = normalize_weights({"slope_deg": 2, "uydurma": 5, "dust_aod": 0, "aridity": 2},
                          load_parameters())
    assert w == {"slope_deg": 0.5, "aridity": 0.5}


@pytest.fixture
def target():
    return Target(id="mars_test", body="mars", name="Test", why="", lat=0, lon=0, params={
        "slope_deg": SourcedValue(value=3, source="test"),
        "aridity": SourcedValue(value=1.0, source="test"),
    })


@pytest.fixture
def grid():
    return pd.DataFrame({
        "id": ["benzer", "orta", "uzak", "eksik"],
        "name": ["Benzer", "Orta", "Uzak", "Eksik"],
        "lat": [0, 1, 2, 3], "lon": [0, 1, 2, 3],
        "slope_deg": [3, 8, 40, None],
        "aridity": [1.0, 0.7, 0.1, None],
    })


def test_ranking_and_scale(grid, target):
    scored = score_grid(grid, target, {"slope_deg": 0.5, "aridity": 0.5})
    assert list(scored.sort_values("score_total", ascending=False)["id"]) == \
        ["benzer", "orta", "uzak", "eksik"]
    assert scored.loc[0, "score_total"] == pytest.approx(100)
    assert scored.loc[3, "score_total"] == pytest.approx(0)  # eksik veri ödüllendirilmez
    assert math.isnan(scored.loc[0, "geology"])  # ağırlığı olmayan boyut


def test_weights_missing_in_target_are_dropped(grid, target):
    # ground_ice hedefte yok -> atılır, sonuç sadece slope'a göre
    scored = score_grid(grid, target, {"slope_deg": 1, "ground_ice": 1})
    assert scored.loc[0, "score_total"] == pytest.approx(100)


def test_top_analogs_contract(grid, target):
    profile = load_profiles()["rover"]
    analogs = top_analogs(grid, target, profile, n=2)
    assert [a.rank for a in analogs] == [1, 2]
    assert analogs[0].id == "benzer"
    assert analogs[0].breakdown[0] == "gravity"
    assert {p.key for p in analogs[0].params} == {"slope_deg", "aridity"}
    assert all(p.match for p in analogs[0].params)
