"""Test profillerini (ağırlık setlerini) ve parametre tanımlarını yükler."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from core.schemas import BREAKDOWN_KEYS, SCORE_KEYS, TEST_IDS, PastTest, Target

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
    # Bu parametrelerde Dünya değeri hedefi aşarsa ceza yok (benzerlik 1). test_profiles.yaml > at_least
    at_least: tuple[str, ...] = ()


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
def load_scoring(path: Path | None = None) -> dict:
    """test_profiles.yaml > missing_data: eksik veri kuralı (core/scoring.py)."""
    data = yaml.safe_load((path or CONFIG_DIR / "test_profiles.yaml").read_text(encoding="utf-8"))
    cfg = {"min_weight_coverage": 0.6, **(data.get("missing_data") or {})}
    if not 0 <= cfg["min_weight_coverage"] <= 1:
        raise ValueError("missing_data.min_weight_coverage 0-1 arasında olmalı")
    return cfg


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
        at_least = tuple(t.get("at_least", []))
        if set(at_least) - set(t["weights"]):
            raise ValueError(f"{test_id}: at_least sadece ağırlığı olan parametreleri içerebilir")
        profiles[test_id] = TestProfile(
            id=test_id,
            label=t["label"],
            weights=normalize_weights(t["weights"], params),
            breakdown=tuple(t.get("breakdown", [])),
            at_least=at_least,
        )
    missing = set(TEST_IDS) - set(profiles)
    if missing:
        raise ValueError(f"Eksik test profilleri: {sorted(missing)}")
    return profiles


def custom_at_least(weights: dict[str, float],
                    profiles: dict[str, TestProfile] | None = None) -> tuple[str, ...]:
    """/scenario (serbest metin) için tek yönlü parametreler.

    Bir parametre, onu ağırlıklandıran HER hazır testte at_least ise serbest metinde de
    tek yönlü sayılır (şu an: carbonate_index, Salda kararı). Hazır testler arasında tutarsız
    ya da hiç tanımlanmamış bir parametre iki yönlü kalır: kural Gemini'ye bırakılmaz.
    """
    profiles = profiles or load_profiles()
    out = []
    for k in weights:
        using = [p for p in profiles.values() if k in p.weights]
        if using and all(k in p.at_least for p in using):
            out.append(k)
    return tuple(out)


# --- Doğrulama seti ve ızgara ayarları -----------------------------------------

SPLITS: tuple[str, ...] = ("tune", "holdout", "report")


@dataclass(frozen=True)
class KnownAnalog:
    id: str
    name: str
    test_id: str
    split: str  # tune: ayar için, holdout: başarı ölçütü için, report: sadece raporlanır
    targets: tuple[str, ...]  # hangi hedef(ler)e göre puanlanır; birden fazlaysa en iyisi
    lat: float
    lon: float
    past_tests: tuple[PastTest, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class KnownSite:
    """Doğrulamada kullanılmayan ama bilinen analog saha: sadece keşiften çıkarılır."""
    id: str
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class ValidationSet:
    analogs: tuple[KnownAnalog, ...]
    exclude_only: tuple[KnownSite, ...]
    exclude_radius_km: float
    top_percent: float
    min_hits: int

    def by_split(self, split: str) -> list[KnownAnalog]:
        return [a for a in self.analogs if a.split == split]

    def all_known_sites(self) -> list[KnownSite]:
        """is_new=False yapılacak tüm yerler: doğrulama seti + exclude_only."""
        return [KnownSite(a.id, a.name, a.lat, a.lon) for a in self.analogs] + list(self.exclude_only)


def load_known_analogs(path: Path | None = None) -> ValidationSet:
    data = yaml.safe_load((path or CONFIG_DIR / "known_analogs.yaml").read_text(encoding="utf-8"))
    target_ids = set(load_targets())
    analogs = []
    for a in data["analogs"]:
        if a["test_id"] not in TEST_IDS:
            raise ValueError(f"{a['id']}: bilinmeyen test_id '{a['test_id']}'")
        if a.get("split") not in SPLITS:
            raise ValueError(f"{a['id']}: split {SPLITS} değerlerinden biri olmalı")
        targets = tuple(a.get("targets") or ())
        if not targets or set(targets) - target_ids:
            raise ValueError(f"{a['id']}: targets boş ya da tanımsız hedef içeriyor {targets}")
        analogs.append(KnownAnalog(
            a["id"], a["name"], a["test_id"], a["split"], targets,
            float(a["lat"]), float(a["lon"]),
            tuple(PastTest(**t) for t in a.get("past_tests") or ()),
            a.get("note", ""),
        ))
    exclude_only = tuple(KnownSite(s["id"], s["name"], float(s["lat"]), float(s["lon"]))
                         for s in data.get("exclude_only") or ())
    ids = [a.id for a in analogs] + [s.id for s in exclude_only]
    if len(ids) != len(set(ids)):
        raise ValueError("known_analogs.yaml: tekrarlanan id var")
    vs = ValidationSet(tuple(analogs), exclude_only, float(data["exclude_radius_km"]),
                       float(data["top_percent"]), int(data["min_hits"]))
    holdout = len(vs.by_split("holdout"))
    if not 0 < vs.min_hits <= holdout:
        raise ValueError(f"min_hits ({vs.min_hits}) 1 ile holdout sayısı ({holdout}) arasında olmalı")
    if not 0 < vs.top_percent <= 100:
        raise ValueError("top_percent 0-100 arasında olmalı")
    return vs


def load_grid_config(path: Path | None = None) -> dict:
    """config/grid.yaml: ızgara boyutu, eğim/pürüzlülük ölçeği ve maske kuralları."""
    data = yaml.safe_load((path or CONFIG_DIR / "grid.yaml").read_text(encoding="utf-8"))
    for section in ("grid", "scale", "masks"):
        if section not in data:
            raise ValueError(f"grid.yaml: '{section}' bölümü eksik")
    for section in ("indices", "ops_tags"):
        if section not in data:
            raise ValueError(f"grid.yaml: '{section}' bölümü eksik")
    params = load_parameters()
    for key in data["indices"]:
        if key not in params:
            raise ValueError(f"grid.yaml > indices: tanımsız parametre '{key}'")
    for key, spec in data["indices"].items():
        breaks = spec.get("breaks")
        if breaks is not None and (len(breaks) != 4 or breaks != sorted(breaks)):
            raise ValueError(f"grid.yaml > indices > {key}: breaks artan 4 değer olmalı")
    if not 0 < data["masks"]["max_masked_fraction"] <= 1:
        raise ValueError("grid.yaml: max_masked_fraction 0-1 arasında olmalı")
    if not 0 <= data["masks"].get("min_land_fraction", 0) <= 1:
        raise ValueError("grid.yaml: min_land_fraction 0-1 arasında olmalı")
    return data
