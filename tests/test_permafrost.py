"""pipeline/permafrost.py: yerel ESA CCI Permafrost NetCDF -> kare başına ground_ice."""
import numpy as np
import pytest

xr = pytest.importorskip("xarray")
pytest.importorskip("netCDF4")

from pipeline.permafrost import cell_fraction, ground_ice_for, load_coarse  # noqa: E402


def write_nc(path, lat0=60.0, lat1=70.0, lon0=-180.0, lon1=180.0, res=0.1, fill=None):
    lat = np.arange(lat0 + res / 2, lat1, res)
    lon = np.arange(lon0 + res / 2, lon1, res)
    pfr = np.full((1, len(lat), len(lon)), np.nan, dtype="float32")
    if fill:
        for (la0, la1, lo0, lo1), v in fill:
            mask = ((lat > la0) & (lat < la1))[:, None] & ((lon > lo0) & (lon < lo1))[None, :]
            pfr[0][mask] = v
    ds = xr.Dataset({"PFR": (("time", "lat", "lon"), pfr)},
                    coords={"time": [np.datetime64("2023-01-01")], "lat": lat, "lon": lon})
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(path)
    return path


def test_percent_to_fraction_and_nan_is_zero(tmp_path):
    f = write_nc(tmp_path / "pf.nc", fill=[((62, 68, 100, 110), 100.0)])
    r = load_coarse(f, factor=2)
    v = cell_fraction(r, np.array([65.0, 65.0]), np.array([105.0, 0.0]), cell_km=25)
    assert v[0] == pytest.approx(1.0) and v[1] == pytest.approx(0.0)


def test_outside_coverage_is_zero(tmp_path):
    f = write_nc(tmp_path / "pf.nc", fill=[((60, 70, -180, 180), 50.0)])
    r = load_coarse(f, factor=2)
    v = cell_fraction(r, np.array([65.0, 10.0, -40.0]), np.array([0.0, 0.0, 0.0]), cell_km=25)
    assert v[0] == pytest.approx(0.5) and v[1] == 0 and v[2] == 0


def test_dateline_wrap(tmp_path):
    f = write_nc(tmp_path / "pf.nc", fill=[((60, 70, 170, 180), 100.0)])  # sadece doğu yakası
    r = load_coarse(f, factor=1)
    v = cell_fraction(r, np.array([65.0]), np.array([179.95]), cell_km=25)
    assert 0.3 < v[0] < 0.7  # kutunun yarısı doğuda (dolu), yarısı batıda (boş)


def test_non_ascii_path_and_no_files(tmp_path):
    import shutil
    src = write_nc(tmp_path / "pf.nc", fill=[((60, 70, -180, 180), 100.0)])  # netCDF ASCII dışı yola yazamaz
    f = tmp_path / "Masaüstü" / "pf.nc"
    f.parent.mkdir()
    shutil.copyfile(src, f)
    assert ground_ice_for(np.array([65.0]), np.array([0.0]), 25, files=[f])[0] == pytest.approx(1.0)
    assert ground_ice_for(np.array([65.0]), np.array([0.0]), 25, files=[]) is None
