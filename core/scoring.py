"""Ağırlıklı benzerlik motoru.

Her parametre için benzerlik:  s = max(0, 1 - |Dünya - hedef| / tolerans)
Boyut skoru (topography, geology, climate, operations): o boyuttaki
parametrelerin ağırlıklı ortalaması. Toplam skor: tüm parametrelerin
ağırlıklı ortalaması. Hepsi 0-100 ölçeğinde.

Hem pipeline/ (hazır sonuçlar) hem api/ (/scenario) bu modülü kullanır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.breakdown import breakdown_for
from core.profiles import Parameter, TestProfile, load_parameters, normalize_weights
from core.schemas import SCORE_KEYS, Analog, AnalogParam, Scores, Target

MATCH_THRESHOLD = 0.5  # parametre benzerliği bunun üstündeyse kartta "benziyor"


def usable_weights(
    weights: dict[str, float], target: Target, params: dict[str, Parameter]
) -> dict[str, float]:
    """Hedefte değeri olmayan parametreleri atıp ağırlıkları yeniden normalize eder."""
    return normalize_weights({k: w for k, w in weights.items() if k in target.params}, params)


def similarity(grid: pd.DataFrame, target: Target, keys: list[str],
               params: dict[str, Parameter]) -> pd.DataFrame:
    """Her kare × parametre için 0-1 benzerlik. Eksik Dünya verisi 0 sayılır."""
    out = {}
    for k in keys:
        earth = grid[k].to_numpy(dtype=float) if k in grid else np.full(len(grid), np.nan)
        s = 1 - np.abs(earth - target.params[k].value) / params[k].tolerance
        out[k] = np.nan_to_num(np.clip(s, 0, 1), nan=0.0)
    return pd.DataFrame(out, index=grid.index)


def score_grid(grid: pd.DataFrame, target: Target, weights: dict[str, float],
               params: dict[str, Parameter] | None = None) -> pd.DataFrame:
    """Izgaraya skor sütunlarını ekler: score_total, topography, ... ve sim_<param>.

    Ağırlığı olmayan boyutların skoru NaN kalır.
    """
    params = params or load_parameters()
    w = usable_weights(weights, target, params)
    if not w:
        raise ValueError("Kullanılabilir ağırlık yok: hedefte bu parametrelerin değeri eksik.")
    sim = similarity(grid, target, list(w), params)

    result = grid.copy()
    result["score_total"] = 100 * sum(sim[k] * wk for k, wk in w.items())
    for dim in SCORE_KEYS:
        dim_w = {k: wk for k, wk in w.items() if params[k].dimension == dim}
        total = sum(dim_w.values())
        result[dim] = (100 * sum(sim[k] * wk for k, wk in dim_w.items()) / total
                       if total else np.nan)
    for k in w:
        result[f"sim_{k}"] = sim[k]
    return result


def top_analogs(grid: pd.DataFrame, target: Target, profile: TestProfile, n: int = 20,
                weights: dict[str, float] | None = None,
                params: dict[str, Parameter] | None = None) -> list[Analog]:
    """En iyi n kareyi veri sözleşmesindeki Analog formatında döndürür.

    grid sütunları: id, name, lat, lon, parametre sütunları; opsiyonel is_new.
    weights verilirse profilin ağırlıkları yerine o kullanılır (/scenario).
    """
    params = params or load_parameters()
    scored = score_grid(grid, target, weights or profile.weights, params)
    best = scored.nlargest(n, "score_total")
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
            rank=rank,
            score_total=round(float(row["score_total"]), 1),
            scores=Scores(**{d: (None if pd.isna(row[d]) else round(float(row[d]), 1))
                             for d in SCORE_KEYS}),
            params=[AnalogParam(
                key=k,
                earth=earth[k],
                target=target.params[k].value,
                source=params[k].earth_source,
                match=bool(row[f"sim_{k}"] >= MATCH_THRESHOLD),
            ) for k in used],
            breakdown=breakdown,
        ))
    return analogs
