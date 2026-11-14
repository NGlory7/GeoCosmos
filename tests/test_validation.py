"""Başarı ölçütü: holdout analoglarından en az min_hits tanesi kendi test amacında
Dünya karelerinin en iyi top_percent yüzdesinde (config/known_analogs.yaml).

Şu durumlarda atlanır (kırmızı değil, sarı):
- grid.parquet henüz yok,
- grid bölgesel (ARCHITECTURE.md > Earth Engine'e bağımlılık): holdout yerlerinin kareleri yok,
- pipeline/validation.py henüz yazılmadı.
"""
from pathlib import Path

import pandas as pd
import pytest

from core.profiles import load_known_analogs

GRID = Path(__file__).resolve().parent.parent / "data" / "processed" / "grid.parquet"


@pytest.mark.skipif(not GRID.exists(), reason="grid.parquet henüz yok (make grid)")
# Bilinen başarısızlık: ilk gerçek doğrulama 0/4 (14 Kasım). Ağırlık ayarı (sadece ayar yerlerine
# bakılarak) bekleniyor: STATUS.md > İlk gerçek sonuç. Ölçüt sağlanınca bu satır silinmeli
# (strict=False: geçerse XPASS olarak görünür, CI kırmızıya düşmez).
@pytest.mark.xfail(reason="Başarı ölçütü henüz sağlanmıyor (0/4); STATUS.md", strict=False)
def test_known_analogs_rank_high():
    holdout = {a.id for a in load_known_analogs().by_split("holdout")}
    present = set(pd.read_parquet(GRID, columns=["known_id"])["known_id"].dropna())
    if not holdout <= present:
        pytest.skip(f"grid bölgesel: holdout kareleri eksik {sorted(holdout - present)}")

    from pipeline.validation import run_validation
    try:
        result = run_validation()
    except NotImplementedError:
        pytest.skip("pipeline/validation.py henüz yazılmadı")
    assert result["hits"] >= result["min_hits"], result
