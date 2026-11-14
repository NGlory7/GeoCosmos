"""Kurulum kolaylığı (core/logistics.py, pipeline/logistics.py): Earth Engine olmadan."""
import json

import pytest

from core import logistics as core
from core.profiles import load_grid_config
from pipeline import logistics as pipe

CFG = load_grid_config()["logistics"]

EASY = {"access_min": 47, "elev_m": 1342.7, "pop_region": 1845485.3, "water_km": 0.1, "water_none": False,
        "plant_km": 40.7, "plant_none": False, "plant": {"name": "X", "fuel": "Gas", "mw": 775, "country": "Turkey"},
        "plant_mw_region": 2020}
HARD = {"access_min": 8473, "elev_m": 693.6, "pop_region": 0.5, "water_km": None, "water_none": True,
        "plant_km": None, "plant_none": True, "plant": None, "plant_mw_region": 0}


def test_ramp_ends_and_direction():
    assert core.ramp(10, 10, 300) == 100 and core.ramp(300, 10, 300) == 0
    assert core.ramp(5, 10, 300) == 100 and core.ramp(1000, 10, 300) == 0  # sınır dışı kırpılır
    assert core.ramp(1e6, 1e6, 1e3) == 100 and core.ramp(1e3, 1e6, 1e3) == 0  # "çok iyi" yönü ters
    assert 0 < core.ramp(50, 10, 300) < 100
    assert core.ramp(0, 1, 100) == 100  # karede su (0 km) log hatası vermez


def test_easy_and_hard_sites():
    e, h = core.score(EASY, CFG), core.score(HARD, CFG)
    assert e["level"] == "Kolay" and h["level"] == "Zor"
    assert e["score"] > 80 > 30 > h["score"]
    # "arama yarıçapında yok" = en kötü, veri yok değil
    assert h["parts"]["power"]["score"] == 0 and h["parts"]["water"]["score"] == 0
    assert "santral yok" in h["parts"]["power"]["text"]


def test_missing_values_are_left_out_not_zero():
    raw = dict(EASY, access_min=None, elev_m=None)
    s = core.score(raw, CFG)
    assert set(s["parts"]) == {"power", "water", "supply"}
    assert "Ulaşım" in s["comment"] and "Yükseklik" in s["comment"]
    assert core.score({}, CFG)["score"] is None


def test_comment_uses_only_raw_numbers():
    s = core.score(HARD, CFG)
    assert core.ADVICE["power"] in s["comment"] and core.ADVICE["water"] in s["comment"]
    assert core.ADVICE["altitude"] not in s["comment"]  # 694 m zayıf değil
    assert "5,9 gün" in s["comment"]  # 8473 dk


def test_people_wording():
    assert core.people(0.5) == "neredeyse kimse yaşamıyor"
    assert core.people(265735.9) == "~266 bin kişi"
    assert core.people(1845485.3) == "~1,8 milyon kişi"


def test_run_offline_rescores_without_earth_engine(tmp_path):
    analogs = tmp_path / "analogs"
    analogs.mkdir()
    feat = {"type": "Feature", "geometry": None, "properties": {"id": "g1", "lat": 1.0, "lon": 2.0}}
    feat2 = {"type": "Feature", "geometry": None, "properties": {"id": "g2", "lat": 3.0, "lon": 4.0}}
    (analogs / "a.geojson").write_text(json.dumps({"features": [feat, feat2]}), encoding="utf-8")
    out = tmp_path / "logistics.json"
    pipe.write({"g1": EASY}, CFG, out)
    rep = pipe.run(analogs, out, online=False)
    assert rep == {"cells": 1, "fetched": 0, "missing": 1, "skipped": "çevrimdışı"}
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["cells"]["g1"]["level"] == "Kolay" and doc["cells"]["g1"]["raw"] == EASY
    assert set(doc["labels"]) == set(core.KEYS)


def test_run_without_file_writes_nothing(tmp_path):
    (tmp_path / "analogs").mkdir()
    pipe.run(tmp_path / "analogs", tmp_path / "logistics.json", online=False)
    assert not (tmp_path / "logistics.json").exists()


@pytest.mark.parametrize("key", core.KEYS)
def test_config_has_every_part(key):
    spec = CFG["scores"][key]
    assert spec["good"] != spec["bad"] and spec["label"]
