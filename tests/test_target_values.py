"""pipeline/target_values.py ve config/targets.yaml: hedef değerleri Dünya ile aynı kuralla mı?"""
import math

import numpy as np
import pytest

from core.profiles import load_targets
from pipeline.features import LEVELS
from pipeline.target_values import _body_radius, cell_means

PIXEL, CELL, WINDOW = 500, 25_000, 5_000


def plane(n: int, slope: float) -> np.ndarray:
    x = np.arange(n) * PIXEL
    return np.tile(x * math.tan(math.radians(slope)), (n, 1))


def test_flat_dem():
    vals = cell_means(np.full((70, 70), 1234.0), PIXEL, CELL, WINDOW)
    assert vals == pytest.approx({"slope_deg": 0, "roughness_m": 0})


def test_tilted_plane():
    vals = cell_means(plane(70, 10), PIXEL, CELL, WINDOW)
    assert vals["slope_deg"] == pytest.approx(10)
    # 11 x 11 pencerede x = -5..5 piksel: std = sqrt(10) piksel
    assert vals["roughness_m"] == pytest.approx(math.tan(math.radians(10)) * PIXEL * math.sqrt(10))


def test_small_dem_rejected():
    with pytest.raises(ValueError):
        cell_means(np.zeros((40, 40)), PIXEL, CELL, WINDOW)


def test_body_radius_parsing():
    assert _body_radius("+proj=longlat +R=3396190 +no_defs") == "+R=3396190"
    assert _body_radius("+proj=eqc +a=1737400 +b=1737400 +units=m") == "+a=1737400 +b=1737400"
    with pytest.raises(ValueError):
        _body_radius("+proj=longlat +datum=WGS84")


# Basamaklı (0/0,25/0,5/0,75/1) sadece mineral indeksleri. ground_ice Dünya'da sürekli bir alan oranı
# (ESA CCI permafrost); hedefte de 0-1 arası herhangi bir değer olabilir (ör. Diviner ısıl kararlılık oranı).
ORDINAL = {"mafic_index", "carbonate_index"}
FRACTION = {"ground_ice", "aridity"}


def test_target_values_are_sane():
    for t in load_targets().values():
        for key, v in t.params.items():
            assert v.source.strip(), (t.id, key)
            if key in ORDINAL:
                assert v.value in LEVELS, (t.id, key, v.value)
            if key in FRACTION:
                assert 0 <= v.value <= 1, (t.id, key, v.value)
        assert t.params["aridity"].value == 1.0, t.id
        if t.body == "moon":
            assert t.params["carbonate_index"].value == 0.0
            assert "dust_aod" not in t.params  # atmosfer yok: parametre yazılmaz
