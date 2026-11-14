"""Ağırlıklı benzerlik motoru.

Her parametre için benzerlik:  s = max(0, 1 - |Dünya - hedef| / tolerans)
  at_least parametrelerinde (test_profiles.yaml) Dünya >= hedef ise s = 1: hedeften fazlası ceza değil.
Boyut skoru (topography, geology, climate): o boyuttaki
parametrelerin ağırlıklı ortalaması. Toplam skor: tüm parametrelerin
ağırlıklı ortalaması. Hepsi 0-100 ölçeğinde.

Eksik Dünya verisi (ör. bulutlu bölgede ASTER boşluğu) "benzemiyor" DEĞİL, "bilinmiyor" demektir:
o karede ağırlıklar ölçülebilen parametrelere dağıtılır. Ölçülebilen ağırlık payı
min_weight_coverage'ın altındaysa skor bu oranla kırpılır (test_profiles.yaml > missing_data):
verisi çoğunlukla eksik bir kare yanlışlıkla üste çıkamaz.

Hem pipeline/ (hazır sonuçlar) hem api/ (/scenario) bu modülü kullanır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.breakdown import breakdown_for
from core.geo import spread_pick
from core.profiles import Parameter, TestProfile, load_parameters, load_scoring, normalize_weights
from core.schemas import SCORE_KEYS, Analog, AnalogParam, Scores, Target

MATCH_THRESHOLD = 0.5  # parametre benzerliği bunun üstündeyse kartta "benziyor"


def usable_weights(
    weights: dict[str, float], target: Target, params: dict[str, Parameter]
) -> dict[str, float]:
    """Hedefte değeri olmayan parametreleri atıp ağırlıkları yeniden normalize eder."""
    return normalize_weights({k: w for k, w in weights.items() if k in target.params}, params)


def similarity(grid: pd.DataFrame, target: Target, keys: list[str],
               params: dict[str, Parameter], at_least: tuple[str, ...] = ()) -> pd.DataFrame:
    """Her kare × parametre için 0-1 benzerlik. Eksik Dünya verisi NaN kalır (score_grid ele alır)."""
    out = {}
    for k in keys:
        earth = grid[k].to_numpy(dtype=float) if k in grid else np.full(len(grid), np.nan)
        diff = earth - target.params[k].value
        if k in at_least:
            diff = np.minimum(diff, 0.0)  # NaN korunur (np.minimum NaN'ı yayar)
        s = 1 - np.abs(diff) / params[k].tolerance
        out[k] = np.clip(s, 0, 1)
    return pd.DataFrame(out, index=grid.index)


def score_grid(grid: pd.DataFrame, target: Target, weights: dict[str, float],
               params: dict[str, Parameter] | None = None, at_least: tuple[str, ...] = ()) -> pd.DataFrame:
    """Izgaraya skor sütunlarını ekler: score_total, topography, ... ve sim_<param>.

    Ağırlığı olmayan boyutların skoru NaN kalır.
    """
    params = params or load_parameters()
    w = usable_weights(weights, target, params)
    if not w:
        raise ValueError("Kullanılabilir ağırlık yok: hedefte bu parametrelerin değeri eksik.")
    sim = similarity(grid, target, list(w), params, at_least)

    min_cov = load_scoring()["min_weight_coverage"]

    def weighted(keys: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """(ölçülebilen parametrelerin ağırlıklı ortalaması, ölçülebilen ağırlık payı)."""
        wk = np.array([w[k] for k in keys])
        s = sim[keys].to_numpy(dtype=float)
        have = ~np.isnan(s)
        num = np.nansum(s * wk, axis=1)
        den = (have * wk).sum(axis=1)
        mean = np.divide(num, den, out=np.full(len(s), np.nan), where=den > 0)
        return mean, den / wk.sum()

    result = grid.copy()
    mean, coverage = weighted(list(w))
    penalty = np.minimum(1.0, coverage / min_cov) if min_cov > 0 else 1.0
    result["score_total"] = np.nan_to_num(100 * mean * penalty, nan=0.0)
    result["coverage"] = coverage
    for dim in SCORE_KEYS:
        keys = [k for k in w if params[k].dimension == dim]
        result[dim] = 100 * weighted(keys)[0] if keys else np.nan
    for k in w:
        result[f"sim_{k}"] = sim[k]
    return result


def top_analogs(grid: pd.DataFrame, target: Target, profile: TestProfile, n: int = 20,
                weights: dict[str, float] | None = None,
                params: dict[str, Parameter] | None = None,
                min_separation_km: float = 0) -> list[Analog]:
    """En iyi n kareyi veri sözleşmesindeki Analog formatında döndürür.

    grid sütunları: id, name, lat, lon, parametre sütunları; opsiyonel is_new ve ops_<etiket>.
    weights verilirse profilin ağırlıkları yerine o kullanılır (/scenario).
    min_separation_km > 0 ise seçilen kareler birbirine bu mesafeden yakın olmaz
    (config/grid.yaml > discovery.min_separation_km).
    """
    params = params or load_parameters()
    scored = score_grid(grid, target, weights or profile.weights, params, profile.at_least)
    ranked = scored.sort_values("score_total", ascending=False, kind="stable")
    if min_separation_km > 0:
        # Sadece en iyi kısımda ara: n * 200 kare, seyrek seçim için fazlasıyla yeter.
        head = ranked.head(max(n * 200, 1000))
        best = head.iloc[spread_pick(head["lat"].to_numpy(float), head["lon"].to_numpy(float),
                                     n, min_separation_km)]
    else:
        best = ranked.head(n)
    used = [c[4:] for c in scored.columns if c.startswith("sim_")]
    breakdown = breakdown_for(target.body, profile)

    analogs = []
    for rank, (_, row) in enumerate(best.iterrows(), start=1):
        earth = {k: (None if pd.isna(row.get(k)) else float(row[k])) for k in used}
        analogs.append(Analog(
            id=str(row["id"]),
            name=str(row.get("name", row["id"])),
            # Varsayılan False: is_new sütunu yoksa hiçbir kare "Yeni aday" diye işaretlenmez.
            # (True olsaydı ünlü analogların yanındaki kareler de yeni aday görünürdü.)
            is_new=bool(row.get("is_new", False)),
            target_id=target.id,
            test_id=profile.id,
            lat=float(row["lat"]),
            lon=float(row["lon"]),
            rank=rank,
            score_total=round(float(row["score_total"]), 1),
            scores=Scores(**{d: (None if pd.isna(row[d]) else round(float(row[d]), 1))
                             for d in SCORE_KEYS}),
            params=[AnalogParam(
                key=k,
                earth=earth[k],
                target=target.params[k].value,
                source=params[k].earth_source,
                match=bool(not pd.isna(row[f"sim_{k}"]) and row[f"sim_{k}"] >= MATCH_THRESHOLD),
            ) for k in used],
            # grid'de ops_<etiket> sütunları varsa (pipeline/features.py) karta taşınır.
            ops_tags={c[4:]: bool(row[c]) for c in scored.columns
                      if c.startswith("ops_") and not pd.isna(row[c])},
            breakdown=breakdown,
        ))
    return analogs
