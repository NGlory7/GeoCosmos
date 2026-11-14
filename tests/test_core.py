"""core/ birim testleri: config dosyaları geçerli mi, motor doğru sıralıyor mu?"""
import math

import pandas as pd
import pytest

from core.profiles import TestProfile as Profile  # "Test" önekiyle pytest toplamasın
from core.profiles import (custom_at_least, load_grid_config, load_known_analogs, load_parameters,
                           load_profiles, load_targets, normalize_weights)
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
    # "uzak" ve "eksik" ikisi de 0 puan: aralarındaki sıra garanti değil, sadece ilk ikisine bakılır.
    assert list(scored.sort_values("score_total", ascending=False)["id"])[:2] == ["benzer", "orta"]
    assert scored.loc[2, "score_total"] == pytest.approx(0)
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


def test_is_new_defaults_to_false(grid, target):
    # Izgarada is_new sütunu yoksa hiçbir kare "Yeni aday" sayılmamalı.
    analogs = top_analogs(grid, target, load_profiles()["rover"], n=2)
    assert not any(a.is_new for a in analogs)


def test_validation_set_split():
    vs = load_known_analogs()
    ids = {a.id for a in vs.analogs}
    assert "dumont_dunes" not in ids
    # Ayar ve test için ayrı yerler: aynı yer iki rolde olamaz.
    assert not {a.id for a in vs.by_split("tune")} & {a.id for a in vs.by_split("holdout")}
    assert vs.min_hits <= len(vs.by_split("holdout"))
    assert [a.id for a in vs.by_split("report")] == ["lanzarote"]


def test_grid_config():
    cfg = load_grid_config()
    assert cfg["scale"]["slope_baseline_m"] > 0
    assert 15 in cfg["masks"]["landcover"]["classes"]  # buz tabakaları maskede (MODIS IGBP 15)


def test_every_test_has_tune_site_or_rationale():
    # Ayar yeri olmayan testin ağırlıkları önceden gerekçelendirilmiş olmalı (test_profiles.yaml).
    import yaml
    from core.profiles import CONFIG_DIR
    tests = yaml.safe_load((CONFIG_DIR / "test_profiles.yaml").read_text(encoding="utf-8"))["tests"]
    tuned = {a.test_id for a in load_known_analogs().by_split("tune")}
    for test_id, t in tests.items():
        assert test_id in tuned or t.get("rationale"), test_id


def test_known_analogs_have_targets_and_exclusions():
    vs = load_known_analogs()
    targets = load_targets()
    for a in vs.analogs:
        assert a.targets and all(t in targets for t in a.targets)
    for a in vs.analogs:  # geçmiş testler gerçek ve kaynaklı olmalı
        assert a.past_tests, a.id
        assert all(t.title.strip() and t.url.startswith("https://") for t in a.past_tests), a.id
    known = {s.id for s in vs.all_known_sites()}
    assert {"dumont_dunes", "holuhraun", "dry_valleys"} <= known


def test_grid_config_indices_match_parameters():
    cfg = load_grid_config()
    assert set(cfg["indices"]) <= set(load_parameters())
    assert {"road_access", "remote"} == set(cfg["ops_tags"])


def test_ops_tags_reach_card(grid, target):
    grid = grid.assign(ops_road_access=[True, False, True, None])
    analogs = top_analogs(grid, target, load_profiles()["rover"], n=2)
    assert analogs[0].ops_tags == {"road_access": True}
    assert "operations" not in analogs[0].scores.model_dump()


def test_analogs_carry_coordinates(grid, target):
    # /scenario yanıtında geometry yok: pin çizilebilmesi için koordinat Analog'da olmalı.
    analogs = top_analogs(grid, target, load_profiles()["rover"], n=2)
    assert [(a.id, a.lat, a.lon) for a in analogs] == [("benzer", 0, 0), ("orta", 1, 1)]


def test_at_least_no_penalty_above_target():
    # Biyo-imza: karbonatta hedeften fazlası ceza değil (Salda kararı, test_profiles.yaml > at_least).
    t = Target(id="t", body="mars", name="T", why="", lat=0, lon=0,
               params={"carbonate_index": SourcedValue(value=0.5, source="test")})
    g = pd.DataFrame({"id": ["az", "esit", "fazla"], "name": ["a", "b", "c"], "lat": [0, 1, 2],
                      "lon": [0, 1, 2], "carbonate_index": [0.25, 0.5, 1.0]})
    w = {"carbonate_index": 1}
    two_sided = score_grid(g, t, w)
    one_sided = score_grid(g, t, w, at_least=("carbonate_index",))
    assert two_sided.loc[2, "score_total"] < 100
    assert one_sided.loc[2, "score_total"] == pytest.approx(100)
    assert one_sided.loc[0, "score_total"] == pytest.approx(two_sided.loc[0, "score_total"])  # altı yine cezalı
    assert load_profiles()["biosignature_carbonate"].at_least == ("carbonate_index",)
    assert load_profiles()["biosignature_arid"].at_least == ()
    assert load_profiles()["rover"].at_least == ()


def test_custom_scenario_inherits_at_least():
    # /scenario: karbonat her hazır testte tek yönlü -> serbest metinde de; diğerleri iki yönlü.
    assert custom_at_least({"carbonate_index": 0.6, "aridity": 0.4}) == ("carbonate_index",)
    assert custom_at_least({"aridity": 1.0}) == ()

    # Hazır testler arasında tutarsızsa tek yönlü sayılmaz (kural Gemini'ye ya da tek teste bırakılmaz).
    base = load_profiles()["biosignature_carbonate"]
    other = Profile(id="rover", label="x", weights={"carbonate_index": 1.0}, breakdown=())
    assert custom_at_least({"carbonate_index": 1.0}, {"biosignature_carbonate": base, "rover": other}) == ()


def test_missing_data_is_unknown_not_mismatch():
    # Eksik veri ağırlığı ölçülebilenlere dağıtır; çoğu eksikse skor kırpılır (missing_data).
    t = Target(id="t", body="mars", name="T", why="", lat=0, lon=0, params={
        "slope_deg": SourcedValue(value=3, source="t"), "aridity": SourcedValue(value=1.0, source="t")})
    g = pd.DataFrame({"id": ["tam", "yarim_eksik", "hepsi_eksik"], "name": ["a", "b", "c"],
                      "lat": [0, 1, 2], "lon": [0, 1, 2],
                      "slope_deg": [3, 3, None], "aridity": [1.0, None, None]})
    s = score_grid(g, t, {"slope_deg": 0.5, "aridity": 0.5})
    assert s.loc[0, "score_total"] == pytest.approx(100)
    # kapsam 0,5 < 0,6: ölçülen kısım mükemmel (100) ama skor 0,5/0,6 oranında kırpılır
    assert s.loc[1, "score_total"] == pytest.approx(100 * 0.5 / 0.6)
    assert s.loc[2, "score_total"] == 0
    s2 = score_grid(g, t, {"slope_deg": 0.7, "aridity": 0.3})  # kapsam 0,7 >= 0,6: ceza yok
    assert s2.loc[1, "score_total"] == pytest.approx(100)


def test_sun_elevation_targets_match_geometry():
    """targets.yaml'daki güneş yüksekliği elle değil, core/geo.py hesabından gelmeli."""
    from core.geo import OBLIQUITY_DEG, mean_noon_sun_elevation
    for t in load_targets().values():
        v = t.params["sun_elevation_deg"].value
        assert abs(v - mean_noon_sun_elevation(t.lat, OBLIQUITY_DEG[t.body])) < 0.06, t.id


def test_sun_elevation_poles_and_equator():
    from core.geo import mean_noon_sun_elevation
    assert abs(mean_noon_sun_elevation(80.0, 23.44) - 10.0) < 1e-9  # |enlem| ≥ ε: tam 90 − |enlem|
    assert 74 < mean_noon_sun_elevation(0.0, 23.44) < 76
