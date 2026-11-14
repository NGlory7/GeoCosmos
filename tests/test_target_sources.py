"""pipeline/diviner_polar.py ve pipeline/mars_climate.py: ağa çıkmadan (sahte yanıtlarla)."""
import pytest

from pipeline import diviner_polar as dp
from pipeline import mars_climate as mc


# --- Diviner PRP -------------------------------------------------------------------------

def fake_row(x, y, temp_k, ice):
    vals = [x, y, -1737.0, x, y, -1737.0, x, y, -1737.0, 0.0, -89.0, 0.0, temp_k, temp_k + 50, ice]
    return ",".join(f"{v:13.5f}" for v in vals)


def test_summarize_cell_box_and_ice_fraction():
    rows = [fake_row(0, 0, 100, 0.5), fake_row(5, 5, 120, -999), fake_row(10, -10, 140, 2.0),
            fake_row(20, 0, 300, 0.1)]  # sonuncu 12,5 km kutunun dışında
    out = dp.summarize(dp.parse(rows), 0.0, 0.0, 12.5)
    assert out["n_triangles"] == 3
    assert out["surface_temp_c"] == pytest.approx(120 - 273.15)
    assert out["ground_ice"] == pytest.approx(1 / 3)  # sadece 0,5 m (≤ 1 m); 2 m ve -999 sayılmaz


def test_cell_rows_cover_box_in_table_order():
    ranges = dp.cell_rows(0.0, 0.0, 12.5)
    assert 54 <= len(ranges) <= 57  # (25 + 2*1) km / 0,5 km ≈ 54 x sütunu + kenar payı
    firsts = [f for f, _ in ranges]
    assert firsts == sorted(firsts) and all(n == ranges[0][1] for _, n in ranges)


def test_polar_values_uses_fetch(monkeypatch):
    calls = []

    def fetch(first, n):
        calls.append((first, n))
        return [fake_row(0, 0, 90, 0.2)]
    v = dp.polar_values("moon_shackleton", fetch=fetch)
    assert calls and v["ground_ice"] == 1.0 and v["surface_temp_c"] == pytest.approx(90 - 273.15)
    with pytest.raises(ValueError):
        dp.polar_values("moon_marius_hills", fetch=fetch)


# --- Mars Climate Database ---------------------------------------------------------------

MCD_HTML = """<ul><li>Surface temperature (K) ..... 250.5</li>
<li>Monthly mean dust column visible optical depth above surface ..... 0.4</li></ul>"""


def test_parse_mcd_html():
    assert mc.parse(MCD_HTML) == {"tsurf_k": 250.5, "dod": 0.4}
    with pytest.raises(ValueError):
        mc.parse("<html>hata</html>")


def test_mars_values_definition_matches_earth():
    def ask(lat, lon, ls, lt):
        return {"tsurf_k": 260.0 if lt == mc.DAY_LT else 200.0, "dod": 0.5}
    v = mc.mars_values("mars_gale", ask=ask, pause_s=0)
    assert v["surface_temp_c"] == pytest.approx(230 - 273.15)  # (gündüz + gece) / 2
    assert v["temp_range_c"] == pytest.approx(60)              # gündüz - gece
    assert v["dust_aod"] == pytest.approx(0.5)
    assert (mc.DAY_LT, mc.NIGHT_LT) == (10.5, 22.5)            # MODIS Terra geçiş saatleri
