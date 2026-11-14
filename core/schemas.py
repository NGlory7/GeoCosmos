"""Veri sözleşmesi: Python tarafı ve frontend aynı formata bağlıdır.

Kaynak: ARCHITECTURE.md > Veri sözleşmesi.
Değişiklik gerekirse önce ARCHITECTURE.md, sonra bu dosya ve
frontend/src/types.ts güncellenir.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Sabit kimlikler ---------------------------------------------------------

Body = Literal["moon", "mars"]
TestId = Literal["rover", "ice_drilling", "lava_tube", "dust", "biosignature_arid", "biosignature_carbonate",
                 "base_site"]
BreakdownKey = Literal["gravity", "atmosphere", "radiation", "liquid_water", "biology", "temperature"]
# Operasyon bilgisi puan değil: Analog.ops_tags (kartta ✓/✗).
ScoreKey = Literal["topography", "geology", "climate"]

BODIES: tuple[str, ...] = ("moon", "mars")
TEST_IDS: tuple[str, ...] = ("rover", "ice_drilling", "lava_tube", "dust", "biosignature_arid",
                             "biosignature_carbonate", "base_site")
BREAKDOWN_KEYS: tuple[str, ...] = ("gravity", "atmosphere", "radiation", "liquid_water", "biology", "temperature")
SCORE_KEYS: tuple[str, ...] = ("topography", "geology", "climate")


# --- Hedef (targets.geojson -> feature.properties) ---------------------------

class SourcedValue(BaseModel):
    value: float
    source: str  # örn. "MOLA" veya "elle — <makale/link>"


class Target(BaseModel):
    id: str
    body: Body
    name: str
    why: str
    lat: float
    lon: float
    params: dict[str, SourcedValue]


# --- Analog (analogs/<hedef>_<test>.geojson -> feature.properties) -----------

class AnalogParam(BaseModel):
    key: str
    earth: float | None
    target: float
    source: str
    match: bool


class PastTest(BaseModel):
    title: str
    url: str


class Scores(BaseModel):
    # None: bu test amacında o boyuta ağırlık verilmemiş (radar grafikte boş gösterilir).
    topography: float | None = Field(default=None, ge=0, le=100)
    geology: float | None = Field(default=None, ge=0, le=100)
    climate: float | None = Field(default=None, ge=0, le=100)


class Analog(BaseModel):
    id: str
    name: str
    is_new: bool
    target_id: str
    test_id: TestId | Literal["custom"]  # "custom": /scenario serbest metin sonucu
    # Karenin Dünya'daki merkezi. /scenario yanıtında geometry olmadığı için pin bundan çizilir.
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    rank: int = Field(ge=1)
    score_total: float = Field(ge=0, le=100)
    scores: Scores
    params: list[AnalogParam]
    ops_tags: dict[str, bool] = {}  # road_access, remote (config/grid.yaml > ops_tags)
    breakdown: list[BreakdownKey]
    past_tests: list[PastTest] = []
    ai_comment: str = ""


# --- API ---------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    target_id: str


class ScenarioResponse(BaseModel):
    weights: dict[str, float]
    unsupported: list[str] = []
    analogs: list[Analog]
