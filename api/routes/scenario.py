"""POST /scenario: serbest metin -> Gemini ağırlıkları -> motor sıralaması."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from api.services import gemini
from core.profiles import TestProfile, load_grid_config, load_parameters, load_targets, normalize_weights
from core.schemas import BREAKDOWN_KEYS, ScenarioRequest, ScenarioResponse
from core.scoring import top_analogs, usable_weights
from pipeline.discovery import name_known_cells

GRID_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "grid.parquet"
TOP_N = 20

router = APIRouter()


@lru_cache
def load_grid() -> pd.DataFrame:
    grid = pd.read_parquet(GRID_PATH)
    # Maskeli kareler (şehir, tarım, su, buz tabakası) öneri olarak dönmez.
    return grid[~grid["masked"]] if "masked" in grid else grid


@router.post("/scenario", response_model=ScenarioResponse)
def scenario(req: ScenarioRequest) -> ScenarioResponse:
    targets = load_targets()
    target = targets.get(req.target_id)
    if target is None:
        raise HTTPException(404, f"Bilinmeyen hedef: {req.target_id}")
    if not GRID_PATH.exists():
        raise HTTPException(503, "grid.parquet henüz üretilmedi (make grid; bkz. STATUS.md).")

    params = load_parameters()
    try:
        raw = gemini.translate(req.text, params)
    except gemini.GeminiError as e:
        raise HTTPException(502, f"Gemini şu an kullanılamıyor: {e}") from e

    weights = normalize_weights(raw.get("weights", {}), params)
    if not usable_weights(weights, target, params):
        raise HTTPException(422, "Bu metinden hedefte karşılığı olan bir parametre çıkarılamadı.")

    profile = TestProfile(id="custom", label=req.text, weights=weights, breakdown=BREAKDOWN_KEYS)
    grid = load_grid()
    analogs = top_analogs(grid, target, profile, n=TOP_N, params=params,
                          min_separation_km=load_grid_config()["discovery"]["min_separation_km"])
    name_known_cells(analogs, grid)
    return ScenarioResponse(weights=weights, unsupported=raw.get("unsupported", []), analogs=analogs)
