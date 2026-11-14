"""Kurulum kolaylığı: aday karenin ham lojistik değerleri -> 0-100 puan + kural tabanlı yorum.

Benzerlik puanına KATILMAZ. Ham değerler pipeline/logistics.py ile Earth Engine'den gelir; buradaki
her şey saf hesaptır (test edilir, CI'da Earth Engine olmadan çalışır). Yorum Gemini değil, kural:
sadece ham değerlerdeki sayıları kullanır, sayı uydurmaz.

Ham değerler (None = veri yok):
  access_min      karenin en erişilebilir noktasından 50 bin+ nüfuslu şehre süre (dakika, MAP 2015)
  plant_km        en yakın santrale mesafe (km, GPPD); plant_search_km içinde yoksa None + plant_none
  plant           {"name", "fuel", "mw", "country"} en yakın santral
  plant_mw_region region_radius_km içindeki toplam kurulu güç (MW)
  water_km        en yakın kalıcı yüzey suyu (km, JRC GSW); water_search_km içinde yoksa None + water_none
  pop_region      region_radius_km içindeki nüfus (kişi, GPW 2020)
  elev_m          karenin ortalama yüksekliği (m, Copernicus DEM)
"""
from __future__ import annotations

import math

KEYS = ("access", "power", "water", "supply", "altitude")

FUEL_TR = {
    "Solar": "güneş", "Wind": "rüzgar", "Hydro": "hidroelektrik", "Gas": "doğal gaz", "Oil": "petrol",
    "Coal": "kömür", "Nuclear": "nükleer", "Geothermal": "jeotermal", "Biomass": "biyokütle",
    "Waste": "atık", "Storage": "depolama", "Cogeneration": "kojenerasyon", "Petcoke": "petrokok",
    "Wave and Tidal": "dalga/gelgit", "Other": "diğer",
}

ADVICE = {
    "access": "Ekip ve malzeme uçak, helikopter ya da sezonluk yolla taşınmalı; taşıma penceresi hava durumuna göre planlanmalı.",
    "power": "Şebekeye bağlanmak gerçekçi değil: güneş paneli + batarya ya da jeneratör ve yakıt deposu baştan kurulmalı.",
    "water": "Su taşınmalı ya da yerinde üretilmeli (kuyu, kar/buz eritme, arıtma); günlük ihtiyaç baştan hesaplanmalı.",
    "supply": "Yakında işgücü ve inşaat malzemesi yok: prefabrik modüller ve yedek parçaların hepsi baştan getirilmeli.",
    "altitude": "Yükseklik ekip sağlığını (irtifa hastalığı) ve jeneratör/motor verimini düşürür; aklimatizasyon planı gerekir.",
}


def ramp(x: float, good: float, bad: float) -> float:
    """good'da 100, bad'de 0, arası logaritmik; iki yönde de çalışır (good < bad ya da good > bad)."""
    lx, lg, lb = (math.log(max(v, 1e-3)) for v in (x, good, bad))
    t = (lx - lb) / (lg - lb)
    return round(100 * min(1.0, max(0.0, t)), 1)


def _fmt(x: float, nd: int = 0) -> str:
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def people(n: float) -> str:
    if n < 100:
        return "neredeyse kimse yaşamıyor"
    if n < 1e6:
        return f"~{_fmt(round(n, -2) if n < 1e4 else round(n, -3) / 1000)}{'' if n < 1e4 else ' bin'} kişi"
    return f"~{_fmt(n / 1e6, 1)} milyon kişi"


def describe(key: str, raw: dict) -> str | None:
    """Kalemin ham değerini okunur metne çevirir; veri yoksa None."""
    if key == "access":
        m = raw.get("access_min")
        if m is None:
            return None
        if m < 120:
            return f"en yakın şehre ~{_fmt(m)} dk"
        return f"en yakın şehre ~{_fmt(m / 60, 1)} saat" if m < 48 * 60 else f"en yakın şehre ~{_fmt(m / 1440, 1)} gün"
    if key == "power":
        if raw.get("plant_none"):
            return "500 km içinde kayıtlı santral yok"
        km, p = raw.get("plant_km"), raw.get("plant") or {}
        if km is None:
            return None
        what = ", ".join(x for x in (FUEL_TR.get(p.get("fuel"), p.get("fuel")), p.get("mw") and f"{_fmt(p['mw'])} MW") if x)
        return f"en yakın santral {_fmt(km)} km" + (f" ({what})" if what else "")
    if key == "water":
        if raw.get("water_none"):
            return "100 km içinde kalıcı göl/nehir yok"
        km = raw.get("water_km")
        if km is None:
            return None
        return "karede kalıcı göl/nehir var" if km < 1 else f"en yakın kalıcı göl/nehir {_fmt(km)} km"
    if key == "supply":
        n = raw.get("pop_region")
        return None if n is None else f"100 km içinde {people(n)}"
    if key == "altitude":
        e = raw.get("elev_m")
        return None if e is None else f"ortalama yükseklik {_fmt(e)} m"
    raise KeyError(key)


def _value(key: str, raw: dict, spec: dict) -> float | None:
    """Puanlanacak sayı; 'arama yarıçapında yok' durumu 'bad' sayılır."""
    if key == "access":
        return raw.get("access_min")
    if key == "power":
        return spec["bad"] if raw.get("plant_none") else raw.get("plant_km")
    if key == "water":
        return spec["bad"] if raw.get("water_none") else raw.get("water_km")
    if key == "supply":
        return raw.get("pop_region")
    if key == "altitude":
        return raw.get("elev_m")
    raise KeyError(key)


def level(score: float, levels: list) -> str:
    for threshold, name in levels:
        if score >= threshold:
            return name
    return levels[-1][1]


def score(raw: dict, cfg: dict) -> dict:
    """cfg: grid.yaml > logistics. Dönüş: {"score", "level", "parts": {k: {label, score, text}}, "comment"}."""
    parts = {}
    for key in KEYS:
        spec = cfg["scores"][key]
        v = _value(key, raw, spec)
        if v is None:
            continue
        parts[key] = {"label": spec["label"], "score": ramp(v, spec["good"], spec["bad"]), "text": describe(key, raw)}
    if not parts:
        return {"score": None, "level": None, "parts": {}, "comment": ""}
    total = round(sum(p["score"] for p in parts.values()) / len(parts), 1)
    lv = level(total, cfg["levels"])
    return {"score": total, "level": lv, "parts": parts, "comment": comment(total, lv, parts, cfg)}


def comment(total: float, lv: str, parts: dict, cfg: dict) -> str:
    good = [p for p in parts.values() if p["score"] >= 70]
    weak = [(k, p) for k, p in parts.items() if p["score"] < 40]
    out = [f"Kurulum kolaylığı {_fmt(total, 1)}/100 ({lv.lower()})."]
    if good:
        out.append("Güçlü yanlar: " + "; ".join(p["text"] for p in good) + ".")
    if weak:
        out.append("Zayıf yanlar: " + "; ".join(p["text"] for _, p in weak) + ".")
        out += [ADVICE[k] for k, _ in weak]
    missing = [cfg["scores"][k]["label"] for k in KEYS if k not in parts]
    if missing:
        out.append(f"Veri yok, puana katılmadı: {', '.join(missing)}.")
    return " ".join(out)
