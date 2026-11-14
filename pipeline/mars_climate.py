"""Mars hedefleri için sıcaklık ve toz: Mars Climate Database (MCD v6.2) web arayüzü.

Kaynak: Mars Climate Database (c) LMD/OU/IAA/ESA/CNES, https://www-mars.lmd.jussieu.fr
(Millour et al., MCD v6). NASA dışı kaynak: sunumda ayrıca atıf yapılır (DATA_SOURCES.md).
Model, TES/MCS/rover ölçümleriyle doğrulanmış bir iklim veritabanıdır; senaryo: iklim ortalaması
(climatology, ortalama Güneş etkinliği).

Dünya tarafıyla AYNI tanım (pipeline/features.py):
  Dünya: MODIS Terra yerel saat ~10:30 (gündüz) ve ~22:30 (gece) yüzey sıcaklığının yıllık ortalaması.
  Mars : MCD yüzey sıcaklığı, yerel saat 10:30 ve 22:30, Mars yılı boyunca 12 mevsim (Ls 0, 30 ... 330).
  surface_temp_c = (gündüz + gece) / 2,  temp_range_c = gündüz - gece.
  dust_aod: aylık ortalama görünür sütun toz optik derinliği (MODIS 550 nm AOD'nin karşılığı), 12 mevsim ortalaması.

Kullanım:  python -m pipeline.mars_climate      (mars_jezero, mars_gale, mars_arcadia; ~1-2 dk)
"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request

import numpy as np

from core.profiles import load_targets

URL = "https://www-mars.lmd.jussieu.fr/mcd_python/cgi-bin/mcdcgi.py"
SOURCE = "Mars Climate Database v6.2 (LMD/ESA/CNES), iklim ortalaması"
LS_VALUES = tuple(range(0, 360, 30))
DAY_LT, NIGHT_LT = 10.5, 22.5   # MODIS Terra geçiş saatleri
MARS_TARGETS = ("mars_jezero", "mars_gale", "mars_arcadia")
_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"


def query(lat: float, lon: float, ls: float, local_time: float) -> dict[str, float]:
    params = {
        "var1": "tsurf", "var2": "dod", "var3": "none", "var4": "none",
        "datekeyhtml": "1", "ls": ls, "localtime": local_time,
        "year": "", "month": "", "day": "", "hours": "", "minutes": "", "seconds": "",
        "julian": "", "martianyear": "", "martianmonth": "", "sol": "",
        "latitude": lat, "longitude": lon % 360, "altitude": "10", "zkey": "3",
        "spacecraft": "none", "isfixedlt": "on", "dust": "1", "hrkey": "1", "averaging": "off",
        "dpi": "80", "islog": "off", "colorm": "jet", "minval": "", "maxval": "", "proj": "cyl",
        "palt": "", "plon": "", "plat": "", "trans": "", "iswind": "off", "latpoint": "", "lonpoint": "",
    }
    with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(params), timeout=120) as r:
        html = r.read().decode("utf-8", "replace")
    return parse(html)


def parse(html: str) -> dict[str, float]:
    t = re.search(r"Surface temperature \(K\)\s*\.+\s*" + _NUM, html)
    d = re.search(r"dust column visible optical depth[^.]*\.+\s*" + _NUM, html)
    if not t or not d:
        raise ValueError("MCD yanıtı beklenen biçimde değil:\n" + html[-600:])
    return {"tsurf_k": float(t.group(1)), "dod": float(d.group(1))}


def mars_values(target_id: str, ask=query, pause_s: float = 0.5) -> dict[str, float]:
    t = load_targets()[target_id]
    if t.body != "mars":
        raise ValueError(f"{target_id} bir Mars hedefi değil")
    day, night, dust = [], [], []
    for ls in LS_VALUES:
        a = ask(t.lat, t.lon, ls, DAY_LT)
        b = ask(t.lat, t.lon, ls, NIGHT_LT)
        day.append(a["tsurf_k"]); night.append(b["tsurf_k"]); dust.append(a["dod"])
        time.sleep(pause_s)  # paylaşılan bir bilim sunucusu: yavaş sor
    d, n = float(np.mean(day)), float(np.mean(night))
    return {"surface_temp_c": (d + n) / 2 - 273.15, "temp_range_c": d - n, "dust_aod": float(np.mean(dust))}


def main() -> None:
    rule = f"yerel saat {DAY_LT:g}/{NIGHT_LT:g}, Ls 0-330 (12 mevsim) ortalaması (pipeline.mars_climate)"
    for tid in MARS_TARGETS:
        v = mars_values(tid)
        print(f"# {tid} — config/targets.yaml > params içine yapıştırın")
        print(f'      surface_temp_c:  {{ value: {v["surface_temp_c"]:.1f}, source: "{SOURCE}; {rule}" }}')
        print(f'      temp_range_c:    {{ value: {v["temp_range_c"]:.1f}, source: "{SOURCE}; {rule}" }}')
        print(f'      dust_aod:        {{ value: {v["dust_aod"]:.2f}, source: "{SOURCE}; görünür toz optik derinliği, {rule}" }}')


if __name__ == "__main__":
    main()
