"""Gemini yokken /scenario: metindeki anahtar kelimeler -> hazır testlerin ağırlıkları.

Kural config/scenario_fallback.yaml'da. Yeni ağırlık uydurulmaz: eşleşen hazır testlerin
(config/test_profiles.yaml) ağırlıklarının ortalaması alınır. Hiçbir test eşleşmezse
FallbackError: arayüz kullanıcıya örnek cümle önerir.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from core.profiles import TestProfile, load_profiles, not_applicable
from core.schemas import Target

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "scenario_fallback.yaml"


class FallbackError(RuntimeError):
    pass


@lru_cache
def load_rules(path: Path = CONFIG_PATH) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    unknown = set(data["tests"]) - set(load_profiles())
    if unknown:
        raise ValueError(f"scenario_fallback.yaml: bilinmeyen test(ler) {sorted(unknown)}")
    return data


def normalize(text: str) -> str:
    """Türkçe küçük harf: 'İ' -> 'i', 'I' -> 'ı' (str.lower 'İ'yi 'i̇' yapar, eşleşme bozulur)."""
    return text.replace("İ", "i").replace("I", "ı").lower()


def _hits(text: str, words: list[str]) -> bool:
    """Anahtar kelime bir kelimenin BAŞINDA geçmeli: Türkçe ekler sona geldiği için "tozlanması" ->
    "toz" eşleşir, ama "okuma" "kum"la, "device" "ice"la, "üstünde" "üs"le eşleşmez (alt dize
    eşleşmesi bunları yanlışlıkla yakalıyordu)."""
    return any(re.search(r"(?<!\w)" + re.escape(normalize(w)), text) for w in words)


def translate(text: str, profiles: dict[str, TestProfile] | None = None, target: Target | None = None) -> dict:
    """gemini.translate ile aynı biçim + method="keywords" ve matched_tests.

    target verilirse o hedefte anlamsız testler (test_profiles.yaml > applies_to; ör. Ay'da toz)
    eşleşmeden atılır: hazır listelerdeki kuralın aynısı."""
    profiles = profiles or load_profiles()
    rules = load_rules()
    t = normalize(text)
    matched = [tid for tid, words in rules["tests"].items() if _hits(t, words)]
    if not matched:
        raise FallbackError("Metinde tanınan bir test anahtar kelimesi yok")
    if target is not None:
        dropped = [tid for tid in matched if not_applicable(profiles[tid], target)]
        matched = [tid for tid in matched if tid not in dropped]
        if not matched:
            labels = ", ".join(profiles[tid].label for tid in dropped)
            raise FallbackError(f"Metindeki test(ler) bu hedefte anlamlı değil: {labels}")

    weights: dict[str, float] = {}
    for tid in matched:
        for k, w in profiles[tid].weights.items():
            weights[k] = weights.get(k, 0.0) + w / len(matched)
    unsupported = [label for label, words in rules.get("unsupported", {}).items() if _hits(t, words)]
    return {"weights": weights, "unsupported": unsupported, "method": "keywords", "matched_tests": matched}
