"""Başarı ölçütü: ünlü analoglardan en az min_hits tanesi kendi test amacında ilk top_n'de.

grid.parquet ve validation adımı hazır olana kadar atlanır.
"""
from pathlib import Path

import pytest

GRID = Path(__file__).resolve().parent.parent / "data" / "processed" / "grid.parquet"


@pytest.mark.skipif(not GRID.exists(), reason="grid.parquet henüz yok (make data)")
def test_known_analogs_rank_high():
    from pipeline.validation import run_validation

    result = run_validation()
    assert result["hits"] >= result["min_hits"], result
