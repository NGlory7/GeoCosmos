"""pipeline/ee_export.py: şerit planı ve kare ızgara hesabı (Earth Engine gerekmez)."""
import math
import re

import pytest

from core.profiles import load_grid_config
from pipeline.ee_export import (M_PER_DEG_LAT, M_PER_DEG_LON_EQ, pixel_deg, plan_stripes, regions,
                                stretch, stripe_name)


@pytest.fixture
def stripes():
    exp = load_grid_config()["export"]
    return plan_stripes(*exp["lat_range"], exp["max_stretch"], exp["max_stripe_deg"]), exp


def test_stripes_cover_range_without_gaps(stripes):
    s, exp = stripes
    assert s[0][0] == exp["lat_range"][0] and s[-1][1] == exp["lat_range"][1]
    assert all(a[1] == b[0] for a, b in zip(s, s[1:]))


def test_stripes_respect_stretch_and_width(stripes):
    s, exp = stripes
    for a, b in s:
        assert b - a <= exp["max_stripe_deg"]
        assert stretch(a, b) <= exp["max_stretch"] + 1e-9, (a, b)
    # kutba yaklaştıkça şeritler daralmalı
    width = {round(a): b - a for a, b in s}
    assert width[min(width, key=lambda k: abs(k - 80))] < width[min(width, key=abs)]


def test_stretch_across_equator():
    assert stretch(-5, 5) == pytest.approx(1 / math.cos(math.radians(5)))
    assert stretch(10, 20) == stretch(-20, -10)


@pytest.mark.parametrize("lat", [0.0, 37.55, 64.85, 79.4])
def test_cells_are_square_on_the_ground(lat):
    # Eski EPSG:6933 ızgarasında 79.4°K'de kare ~5 x 117 km'ydi; şimdi her enlemde 25 x 25 km.
    dx, dy = pixel_deg(25_000, lat)
    ew = dx * M_PER_DEG_LON_EQ * math.cos(math.radians(lat))
    ns = dy * M_PER_DEG_LAT
    assert ew == pytest.approx(25_000) and ns == pytest.approx(25_000)


def test_task_names_valid_and_unique():
    names = [n for n, _ in regions(25)] + [n for n, _ in regions(5, (28, 36, 31, 39))]
    assert len(names) == len(set(names))
    for n in names:
        assert re.fullmatch(r"[A-Za-z0-9.,:;_-]{1,100}", n), n
    assert stripe_name(25, -86) == "grid25km_lat86.00S"


def test_tiles_stay_under_pixel_limit():
    # Earth Engine: tek görevde en fazla 2^31 kaynak piksel; 30 m DEM'de karo <= max_tile_deg2.
    exp = load_grid_config()["export"]
    for name, (x0, y0, x1, y1) in regions(25):
        assert (x1 - x0) * (y1 - y0) <= exp["max_tile_deg2"] + 1e-6, name
        assert ((x1 - x0) * 3600) * ((y1 - y0) * 3600) < 2**31, name  # 1 yay saniyesi ≈ 30 m
    # karolar boylamda boşluksuz: her şeridin parçaları -180..180'i kaplar
    by_stripe = {}
    for name, (x0, _, x1, _) in regions(25):
        by_stripe.setdefault(name.split("_x")[0], []).append((x0, x1))
    for parts in by_stripe.values():
        parts.sort()
        assert parts[0][0] == -180 and abs(parts[-1][1] - 180) < 1e-3
        assert all(abs(a[1] - b[0]) < 1e-3 for a, b in zip(parts, parts[1:]))
