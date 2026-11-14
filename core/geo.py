"""Küçük coğrafi yardımcılar (core/ ve pipeline/ ortak kullanır)."""
from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Büyük daire uzaklığı (km). Dizi ya da sayı alır."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def spread_pick(lat: np.ndarray, lon: np.ndarray, n: int, min_sep_km: float) -> list[int]:
    """Sıralı (en iyi önce) adaylardan, seçilenlere min_sep_km'den yakın olmayan ilk n tanesinin
    konumları. Aynı çölün komşu karelerinin listeyi doldurmasını önler."""
    picked: list[int] = []
    for i in range(len(lat)):
        if min_sep_km <= 0 or not picked or \
                np.all(haversine_km(lat[i], lon[i], lat[picked], lon[picked]) >= min_sep_km):
            picked.append(i)
            if len(picked) == n:
                break
    return picked


# Ekvatorun yörünge düzlemine eğikliği (°). Güneşin yıl içindeki deklinasyon aralığını belirler.
#   Dünya 23,44 (IAU); Mars 25,19 (NASA Mars Fact Sheet); Ay 1,54 = ekvatorun ekliptiğe eğikliği
#   (NASA Moon Fact Sheet; Ay'dan bakınca Güneş'in deklinasyonu bu kadar salınır).
OBLIQUITY_DEG = {"earth": 23.44, "mars": 25.19, "moon": 1.54}


def mean_noon_sun_elevation(lat, obliquity_deg: float, samples: int = 360):
    """Yıllık ortalama öğlen güneş yüksekliği (°): 90 − |enlem − deklinasyon|, deklinasyon
    δ = asin(sin ε · sin L) ile yıl boyunca eşit aralıklı L üzerinden ortalanır.

    Geometriktir: yerel ufuk (dağ, krater duvarı) ve yörünge dışmerkezliği hesaba katılmaz.
    Kutup gecesinde öğlen yüksekliği negatiftir ve ortalamaya öyle girer (güneş hiç doğmaz).
    |enlem| ≥ ε olan her yerde sonuç tam olarak 90 − |enlem|'dir.
    """
    lat = np.asarray(lat, dtype=float)
    lon_sun = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    dec = np.degrees(np.arcsin(np.sin(np.radians(obliquity_deg)) * np.sin(lon_sun)))
    elev = 90 - np.abs(lat[..., None] - dec)
    out = elev.mean(axis=-1)
    return float(out) if out.ndim == 0 else out
