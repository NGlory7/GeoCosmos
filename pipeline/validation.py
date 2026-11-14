"""Ünlü analog testi -> frontend/public/data/validation.json.

Her bilinen analog (config/known_analogs.yaml) kendi test amacında ve kendi hedef(ler)inde,
Dünya karelerinin yüzde kaçlık diliminde?

- Yüzdelik paydası: maskeli olmayan kareler + doğrulama yerlerinin kendi kareleri (known_id).
- Sıra: 1 + (bu yerden yüksek puan alan kare sayısı). Yüzdelik = sıra / payda * 100.
- Birden fazla hedef varsa en iyi (en küçük) yüzdelik alınır.
- split=holdout: başarı ölçütü (en az min_hits tanesi en iyi top_percent içinde).
- split=tune:    sırası raporlanır; ağırlık ayarı sadece bunlara bakılarak yapılır.
- split=report:  sırası raporlanır, ölçüte girmez (ör. Lanzarote: lav tüpü verilerde görünmüyor).

Dönüş: {"hits", "min_hits", "holdout_total", "top_percent", "passed", "denominator", "analogs": [...]}
Her analog kaydında "status": ok | missing_cell (grid'de karesi yok, ör. bölgesel grid)
| no_target_values (hedefte bu testin parametrelerinden hiçbiri yok).

Kullanım:  python -m pipeline.validation
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.profiles import load_known_analogs, load_parameters, load_profiles, load_targets
from core.scoring import score_grid, usable_weights

ROOT = Path(__file__).resolve().parent.parent
GRID_PATH = ROOT / "data" / "processed" / "grid.parquet"
OUT_PATH = ROOT / "frontend" / "public" / "data" / "validation.json"


def denominator(grid: pd.DataFrame) -> pd.DataFrame:
    if "masked" not in grid:
        return grid
    known = grid["known_id"].notna() if "known_id" in grid else False
    return grid[~grid["masked"] | known]


def rank_of(scores: pd.Series, value: float) -> int:
    return int((scores > value).sum()) + 1


def run_validation(grid: pd.DataFrame | None = None) -> dict:
    if grid is None:
        grid = pd.read_parquet(GRID_PATH)
    vs = load_known_analogs()
    targets, profiles, params = load_targets(), load_profiles(), load_parameters()
    pool = denominator(grid).reset_index(drop=True)
    n = len(pool)
    rows = []
    for a in vs.analogs:
        rec = {"id": a.id, "name": a.name, "test_id": a.test_id, "split": a.split,
               "targets": list(a.targets), "note": a.note,
               "past_tests": [t.model_dump() for t in a.past_tests]}
        cell = pool.index[pool["known_id"] == a.id] if "known_id" in pool else []
        if len(cell) == 0:
            rows.append({**rec, "status": "missing_cell"})
            continue
        i = cell[0]
        best = None
        for tid in a.targets:
            target, profile = targets[tid], profiles[a.test_id]
            if not usable_weights(profile.weights, target, params):
                continue
            scored = score_grid(pool, target, profile.weights, params, profile.at_least)
            s = float(scored.loc[i, "score_total"])
            r = rank_of(scored["score_total"], s)
            cand = {"target_id": tid, "score_total": round(s, 1), "rank": r,
                    "percentile": round(r / n * 100, 3)}
            if best is None or cand["percentile"] < best["percentile"]:
                best = cand
        if best is None:
            rows.append({**rec, "status": "no_target_values"})
            continue
        rows.append({**rec, "status": "ok", **best, "cell_id": str(pool.loc[i, "id"]),
                     "hit": best["percentile"] <= vs.top_percent})
    holdout = [r for r in rows if r["split"] == "holdout"]
    hits = sum(1 for r in holdout if r.get("hit"))
    return {"hits": hits, "min_hits": vs.min_hits, "holdout_total": len(holdout),
            "top_percent": vs.top_percent, "passed": hits >= vs.min_hits,
            "denominator": n, "analogs": rows}


def write_validation(result: dict, out: Path = OUT_PATH) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run_validation()
    write_validation(res)
    print(f"sınav: {res['hits']}/{res['holdout_total']} isabet (gereken {res['min_hits']}), "
          f"en iyi %{res['top_percent']:g}, payda {res['denominator']} kare -> "
          f"{'GEÇTİ' if res['passed'] else 'GEÇMEDİ'}")
    for r in res["analogs"]:
        extra = f"%{r['percentile']:.2f} ({r['target_id']})" if r["status"] == "ok" else r["status"]
        print(f"  [{r['split']:7s}] {r['name']}: {extra}")
