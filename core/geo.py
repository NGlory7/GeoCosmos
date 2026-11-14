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
