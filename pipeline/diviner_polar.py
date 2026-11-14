"""Ay kutup hedefleri için Diviner değerleri: PDS Diviner Polar Resource Product (PRP).

Ürün: LRO-L-DLRE-5-PRP-V2.0, dlre_prp_south.tab (PDS Geosciences Node, challenge listesi:
"NASA LRO Diviner Lunar Data"). 605 MB'lık sabit uzunluklu ASCII tablo; hepsi indirilmez,
sadece hedef karesine düşen satırlar HTTP aralık isteğiyle okunur (hedef başına ~1 MB).

Tablo düzeni (satır = 210 bayt, ilk satır başlık):
  1200 x 1200 kare, 0,5 km adımlı Kartezyen x/y ızgara (x: +300 -> -300 km dış döngü,
  y: -300 -> +300 km iç döngü), her karede 2 üçgen: satır = (i * 1200 + j) * 2 + t.
  Sütunlar: üçgen köşeleri (x, y, z km), merkez boylam/enlem/yükseklik, temp_avg (yıllık
  ortalama, K), temp_max (yıllık en yüksek, K), ice_depth (buzun kararlı olduğu derinlik, m;
  -999 = kararlı değil).

Hedef karesi: hedef merkezli 25 km x 25 km (config/grid.yaml > grid.coarse_km), kutup düzleminde.

Üretilen değerler (kare ortalaması):
  surface_temp_c: temp_avg ortalaması (°C). Dünya'da (gündüz+gece)/2; burada yıllık ortalama
                  doğrudan ölçülmüş olduğu için en yakın karşılık.
  ground_ice:     ice_depth 0..ice_max_depth_m (1 m) arasında olan alan oranı (0-1). Dünya'daki
                  permafrost oranının karşılığı: "karenin ne kadarında yüzeye yakın donmuş zemin var".
  temp_range_c:   ÜRETİLMEZ: üründe en düşük sıcaklık yok (sadece ortalama ve en yüksek).

Kullanım:  python -m pipeline.diviner_polar      (moon_shackleton, moon_malapert)
"""
from __future__ import annotations

import math
import urllib.request

import numpy as np

from core.profiles import load_grid_config, load_targets

URL = ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
       "data_derived_prp/dlre_prp_south.tab")
SOURCE = "Diviner PRP (PDS, LRO-L-DLRE-5-PRP-V2.0, dlre_prp_south)"
ROW_BYTES = 210
N = 1200            # ızgara kenarı (kare)
STEP_KM = 0.5
HALF_KM = 300.0
R_MOON_KM = 1737.4
ICE_MAX_DEPTH_M = 1.0
POLAR_TARGETS = ("moon_shackleton", "moon_malapert")


def to_xy(lat: float, lon: float) -> tuple[float, float]:
    c = R_MOON_KM * math.cos(math.radians(lat))
    return c * math.cos(math.radians(lon)), c * math.sin(math.radians(lon))


def fetch_rows(first_row: int, n_rows: int, url: str = URL) -> list[str]:
    start = ROW_BYTES * (1 + first_row)  # 1 başlık satırı
    req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start + ROW_BYTES * n_rows - 1}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("ascii").splitlines()


def parse(lines: list[str]) -> np.ndarray:
    """Dönüş: (n, 4) = merkez x, merkez y, temp_avg K, ice_depth m."""
    out = []
    for ln in lines:
        f = [float(v) for v in ln.split(",")]
        out.append(((f[0] + f[3] + f[6]) / 3, (f[1] + f[4] + f[7]) / 3, f[12], f[14]))
    return np.array(out)


def cell_rows(x0: float, y0: float, half_km: float, margin_km: float = 1.0) -> list[tuple[int, int]]:
    """(ilk satır, satır sayısı) aralıkları: x sütunu başına bir aralık."""
    i_lo = max(0, int((HALF_KM - (x0 + half_km + margin_km)) / STEP_KM))
    i_hi = min(N - 1, int((HALF_KM - (x0 - half_km - margin_km)) / STEP_KM) + 1)
    j_lo = max(0, int((y0 - half_km - margin_km + HALF_KM) / STEP_KM))
    j_hi = min(N - 1, int((y0 + half_km + margin_km + HALF_KM) / STEP_KM) + 1)
    return [((i * N + j_lo) * 2, (j_hi - j_lo + 1) * 2) for i in range(i_lo, i_hi + 1)]


def summarize(tri: np.ndarray, x0: float, y0: float, half_km: float) -> dict[str, float]:
    inside = (np.abs(tri[:, 0] - x0) <= half_km) & (np.abs(tri[:, 1] - y0) <= half_km)
    t = tri[inside]
    if len(t) == 0:
        raise ValueError("kare içinde üçgen yok")
    ice = (t[:, 3] >= 0) & (t[:, 3] <= ICE_MAX_DEPTH_M)
    return {"surface_temp_c": float(t[:, 2].mean() - 273.15),
            "ground_ice": float(ice.mean()),
            "n_triangles": int(len(t))}


def polar_values(target_id: str, fetch=fetch_rows) -> dict[str, float]:
    t = load_targets()[target_id]
    if t.body != "moon" or t.lat > -76:
        raise ValueError(f"{target_id}: güney kutbu ürünü sadece 76°G'nin güneyini kapsar")
    half = load_grid_config()["grid"]["coarse_km"] / 2
    x0, y0 = to_xy(t.lat, t.lon)
    lines: list[str] = []
    for first, n in cell_rows(x0, y0, half):
        lines += fetch(first, n)
    return summarize(parse(lines), x0, y0, half)


def main() -> None:
    for tid in POLAR_TARGETS:
        v = polar_values(tid)
        rule = f"25 km kare ortalaması, {v['n_triangles']} üçgen (pipeline.diviner_polar)"
        print(f"# {tid} — config/targets.yaml > params içine yapıştırın")
        print(f'      surface_temp_c:  {{ value: {v["surface_temp_c"]:.1f}, source: "{SOURCE}, temp_avg → {rule}" }}')
        print(f'      ground_ice:      {{ value: {v["ground_ice"]:.2f}, source: "{SOURCE}, ice_depth ≤ {ICE_MAX_DEPTH_M:g} m alan oranı → {rule}" }}')


if __name__ == "__main__":
    main()
