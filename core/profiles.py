"""Test profillerini (ağırlık setlerini) ve parametre tanımlarını yükler."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from core.schemas import BREAKDOWN_KEYS, SCORE_KEYS, TEST_IDS, Target

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    dimension: str
    tolerance: float
    earth_source: str


@dataclass(frozen=True)
class TestProfile:
    id: str
    label: str
    weights: dict[str, float]
    breakdown: tuple[str, ...]


def normalize_weights(weights: dict[str, float], allowed: set[str] | dict) -> dict[str, float]:
    """Bilinmeyen ve pozitif olmayan anahtarları atar, toplamı 1'e getirir.

    Hem YAML profilleri hem Gemini'nin ürettiği ağırlıklar bu kontrolden geçer.
    """
    clean = {k: float(v) for k, v in weights.items() if k in allowed and float(v) > 0}
    total = sum(clean.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in clean.items()}


@lru_cache
def load_parameters(path: Path | None = None) -> dict[str, Parameter]:
    data = yaml.safe_load((path or CONFIG_DIR / "test_profiles.yaml").read_text(encoding="utf-8"))
    params: dict[str, Parameter] = {}
    for key, p in data["parameters"].items():
        if p["dimension"] not in SCORE_KEYS:
            raise ValueError(f"{key}: bilinmeyen dimension '{p['dimension']}'")
        if p["tolerance"] <= 0:
            raise ValueError(f"{key}: tolerance pozitif olmalı")
        params[key] = Parameter(key, p["label"], p["dimension"], float(p["tolerance"]), p["earth_source"])
    return params


def load_targets(path: Path | None = None) -> dict[str, Target]:
    data = yaml.safe_load((path or CONFIG_DIR / "targets.yaml").read_text(encoding="utf-8"))
    params = load_parameters()
    targets: dict[str, Target] = {}
    for t in data["targets"]:
        target = Target(**t)
        unknown = set(target.params) - set(params)
        if unknown:
            raise ValueError(f"{target.id}: tanımsız parametre(ler) {sorted(unknown)}")
        targets[target.id] = target
    return targets


@lru_cache
def load_profiles(path: Path | None = None) -> dict[str, TestProfile]:
    path = path or CONFIG_DIR / "test_profiles.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    params = load_parameters(path)
    profiles: dict[str, TestProfile] = {}
    for test_id, t in data["tests"].items():
        if test_id not in TEST_IDS:
            raise ValueError(f"Bilinmeyen test_id: {test_id}")
        unknown = set(t["weights"]) - set(params)
        if unknown:
            raise ValueError(f"{test_id}: tanımsız parametre(ler) {sorted(unknown)}")
        bad = set(t.get("breakdown", [])) - set(BREAKDOWN_KEYS)
        if bad:
            raise ValueError(f"{test_id}: bilinmeyen breakdown {sorted(bad)}")
        profiles[test_id] = TestProfile(
            id=test_id,
            label=t["label"],
            weights=normalize_weights(t["weights"], params),
            breakdown=tuple(t.get("breakdown", [])),
        )
    missing = set(TEST_IDS) - set(profiles)
    if missing:
        raise ValueError(f"Eksik test profilleri: {sorted(missing)}")
    return profiles
