"""POST /scenario: serbest metin -> ağırlıklar -> motor sıralaması.

Ağırlık kaynağı sırası: Gemini önbelleği -> Gemini -> anahtar kelime yedeği
(config/scenario_fallback.yaml). Yedek sadece hazır testlerin ağırlıklarını kullanır.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from api import grid_source
from api.services import fallback, gemini
from core.profiles import (TestProfile, custom_at_least, load_grid_config, load_parameters,
                           load_targets, normalize_weights)
from core.schemas import BREAKDOWN_KEYS, ScenarioRequest, ScenarioResponse
from core.scoring import top_analogs, usable_weights
from pipeline.discovery import name_known_cells
from pipeline.placenames import attach_places
from pipeline.placenames import load_cache as load_place_cache

GRID_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "grid.parquet"
TOP_N = 20

router = APIRouter()
log = logging.getLogger("geocosmos.scenario")


@lru_cache
def load_grid() -> pd.DataFrame:
    grid = pd.read_parquet(GRID_PATH)
    # Maskeli kareler (şehir, tarım, su, buz tabakası) öneri olarak dönmez.
    return grid[~grid["masked"]] if "masked" in grid else grid


def translate(text: str, params, target) -> dict:
    """Gemini (önbellek dahil); ulaşılamazsa anahtar kelime yedeği. İkisi de olmazsa 503.
    Yedek sadece bu hedefte anlamlı hazır testleri kullanır (test_profiles.yaml > applies_to)."""
    try:
        return gemini.translate(text, params)
    except gemini.GeminiError as gem_err:
        try:
            return fallback.translate(text, target=target)
        except fallback.FallbackError as fb_err:
            # Ham Gemini hatası (uzun, faturalandırma bağlantıları) kullanıcıya gösterilmez, sadece kayda.
            why = "günlük kota doldu" if "429" in str(gem_err) else "ulaşılamadı"
            log.warning("Gemini kullanılamadı, yedek de eşleşmedi: %s", gem_err)
            raise HTTPException(
                503,
                f"Gemini şu an kullanılamıyor ({why}). {fb_err}. "
                "Bu hedefte anlamlı bir test amacı yazın (ör. rover sürüşü, üs kurulumu, buz sondajı).",
            ) from gem_err


@router.post("/scenario", response_model=ScenarioResponse)
def scenario(req: ScenarioRequest) -> ScenarioResponse:
    targets = load_targets()
    target = targets.get(req.target_id)
    if target is None:
        raise HTTPException(404, f"Bilinmeyen hedef: {req.target_id}")
    if not GRID_PATH.exists():
        if grid_source.downloading():
            raise HTTPException(503, "Dünya ızgarası indiriliyor; birkaç dakika sonra tekrar deneyin.")
        raise HTTPException(503, "grid.parquet henüz üretilmedi (make grid; bkz. STATUS.md).")

    params = load_parameters()
    raw = translate(req.text, params, target)

    weights = normalize_weights(raw.get("weights", {}), params)
    if not usable_weights(weights, target, params):
        raise HTTPException(422, "Bu metinden hedefte karşılığı olan bir parametre çıkarılamadı.")

    # Tek yönlü kurallar (ör. biyo-imzada karbonat) serbest metinde de aynı: hazır testlerden gelir.
    profile = TestProfile(id="custom", label=req.text, weights=weights, breakdown=BREAKDOWN_KEYS,
                          at_least=custom_at_least(weights))
    grid = load_grid()
    analogs = top_analogs(grid, target, profile, n=TOP_N, params=params,
                          min_separation_km=load_grid_config()["discovery"]["min_separation_km"])
    name_known_cells(analogs, grid)
    attach_places(analogs, load_place_cache())  # sadece önbellek; serbest metnin yeni kareleri koordinatla kalır
    return ScenarioResponse(
        method=raw.get("method", "gemini"),
        matched_tests=raw.get("matched_tests", []),
        weights=weights,
        unsupported=raw.get("unsupported", []),
        analogs=analogs,
    )
