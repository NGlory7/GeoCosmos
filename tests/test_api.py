"""api/ testleri: CORS, senaryo yedeği (Gemini yokken), grid.parquet indirme, /health."""
import math

import pytest

from api.main import DEFAULT_ORIGINS, parse_origins
from api.services import fallback, gemini
from core.profiles import load_profiles, load_targets


def test_parse_origins_list_and_trailing_slash():
    raw = " http://localhost:5173 , https://geocosmos.vercel.app/ ,"
    assert parse_origins(raw) == ["http://localhost:5173", "https://geocosmos.vercel.app"]


def test_parse_origins_empty_falls_back_to_defaults():
    assert parse_origins(None) == list(DEFAULT_ORIGINS)
    assert parse_origins("  ") == list(DEFAULT_ORIGINS)
    assert "http://127.0.0.1:5173" in DEFAULT_ORIGINS


# --- Senaryo yedeği: Gemini yokken anahtar kelime -> hazır testler ---------------------------

def test_fallback_turkish_case_and_substring():
    # "TOZLANMASINI" büyük harf + ek: yine toz testine eşlenmeli; İ/ı bozulmamalı
    r = fallback.translate("Güneş panelinin TOZLANMASINI test etmek İSTİYORUM")
    assert r["method"] == "keywords"
    assert r["matched_tests"] == ["dust"]
    assert r["weights"] == pytest.approx(load_profiles()["dust"].weights)


def test_fallback_averages_matched_tests_and_flags_unsupported():
    r = fallback.translate("Donmuş zeminde matkapla buz sondajı, düşük yerçekiminde rover sürüşü")
    assert set(r["matched_tests"]) == {"ice_drilling", "rover"}
    assert math.isclose(sum(r["weights"].values()), 1.0)
    p = load_profiles()
    assert r["weights"]["ground_ice"] == pytest.approx(p["ice_drilling"].weights["ground_ice"] / 2)
    assert r["unsupported"] == ["düşük yerçekimi"]


def test_fallback_no_match_raises():
    with pytest.raises(fallback.FallbackError):
        fallback.translate("merhaba dünya")


def test_fallback_config_tests_exist():
    assert set(fallback.load_rules()["tests"]) <= set(load_profiles())
    # Hazır testlerin hepsinin anahtar kelimesi olmalı (biyo-imza bölündü, üs kurulumu eklendi)
    assert set(fallback.load_rules()["tests"]) == set(load_profiles())


def test_fallback_matches_word_starts_only():
    # Alt dize değil kelime başı: "okuma" kum (toz) değil, "device" ice (buz) değil, "üstünde" üs değil
    with pytest.raises(fallback.FallbackError):
        fallback.translate("okuma notu: device üstünde")
    assert fallback.translate("Ay üssü kurmak için iniş alanı")["matched_tests"] == ["base_site"]


def test_fallback_respects_target_applicability():
    # Hazır listelerdeki kural (test_profiles.yaml > applies_to): Ay'da toz testi yok.
    targets = load_targets()
    with pytest.raises(fallback.FallbackError, match="anlamlı değil"):
        fallback.translate("toz fırtınası", target=targets["moon_shackleton"])
    r = fallback.translate("rover sürüşü ve toz", target=targets["moon_malapert"])
    assert r["matched_tests"] == ["rover"]  # toz atıldı, rover kaldı
    assert fallback.translate("toz fırtınası", target=targets["mars_gale"])["matched_tests"] == ["dust"]


@pytest.fixture
def scenario_client(tmp_path, monkeypatch):
    import pandas as pd
    from fastapi.testclient import TestClient

    from api.main import app
    from api.routes import scenario as sc

    grid = pd.DataFrame({
        "id": ["a", "b"], "name": ["A", "B"], "lat": [10.0, -30.0], "lon": [20.0, 60.0],
        "aridity": [0.9, 0.2], "dust_aod": [0.4, 0.1], "slope_deg": [3.0, 10.0],
        "roughness_m": [2.0, 9.0], "temp_range_c": [30.0, 10.0], "masked": [False, False],
    })
    grid.to_parquet(tmp_path / "grid.parquet")
    monkeypatch.setattr(sc, "GRID_PATH", tmp_path / "grid.parquet")
    sc.load_grid.cache_clear()
    yield TestClient(app), sc
    sc.load_grid.cache_clear()


def test_scenario_uses_fallback_when_gemini_down(scenario_client, monkeypatch):
    client, sc = scenario_client

    def down(text, params):
        raise gemini.GeminiError("GEMINI_API_KEY tanımlı değil")

    monkeypatch.setattr(sc.gemini, "translate", down)
    r = client.post("/scenario", json={"text": "Toz fırtınasında aşınma", "target_id": "mars_gale"})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "keywords" and body["matched_tests"] == ["dust"]
    assert body["analogs"]

    r = client.post("/scenario", json={"text": "merhaba", "target_id": "mars_gale"})
    assert r.status_code == 503
    assert "test amacı" in r.json()["detail"]


def test_scenario_reports_gemini_method(scenario_client, monkeypatch):
    client, sc = scenario_client
    monkeypatch.setattr(sc.gemini, "translate",
                        lambda t, p: {"weights": {"aridity": 1}, "unsupported": [], "method": "cache"})
    r = client.post("/scenario", json={"text": "kurak", "target_id": "mars_gale"})
    assert r.status_code == 200
    assert r.json()["method"] == "cache" and r.json()["matched_tests"] == []


# --- grid.parquet indirme (GRID_URL) ---------------------------------------------------------

def test_grid_download_is_atomic(tmp_path):
    from api import grid_source

    src = tmp_path / "src.parquet"
    src.write_bytes(b"PAR1-test")
    dest = tmp_path / "out" / "grid.parquet"
    grid_source.download(src.as_uri(), dest)
    assert dest.read_bytes() == b"PAR1-test"
    assert not dest.with_suffix(".parquet.part").exists()


def test_grid_start_skips_when_present_or_no_url(tmp_path, monkeypatch):
    from api import grid_source

    monkeypatch.delenv("GRID_URL", raising=False)
    assert grid_source.start(tmp_path / "grid.parquet") is False  # URL yok
    present = tmp_path / "var.parquet"
    present.write_bytes(b"x")
    assert grid_source.start(present, url="file:///yok") is False  # dosya zaten var


def test_health_reports_status():
    from fastapi.testclient import TestClient

    from api.main import app

    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok"
    assert set(body) >= {"grid", "gemini", "grid_downloading"}
