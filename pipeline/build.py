"""make data: tüm offline adımları sırayla çalıştırır ve frontend/public/data/ dosyalarını üretir.

Şu an sadece targets.geojson üretiliyor; diğer adımlar yazıldıkça açılacak.
Çalıştırma:  python -m pipeline.build
"""
from __future__ import annotations

import json
from pathlib import Path

from core.profiles import load_profiles, load_targets

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "public" / "data"


def write_targets() -> Path:
    features = []
    for t in load_targets().values():
        props = t.model_dump(exclude={"lat", "lon"})
        features.append({
            "type": "Feature",
            # Not: koordinatlar ilgili gök cismindedir (Ay/Mars), Dünya değil.
            "geometry": {"type": "Point", "coordinates": [t.lon, t.lat]},
            "properties": props,
        })
    path = OUT_DIR / "targets.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    load_profiles()  # config hatalarını en başta yakala
    print("yazıldı:", write_targets().relative_to(ROOT))
    # TODO: ee_export -> features -> discovery -> analogs -> commentary -> heatmap -> validation


if __name__ == "__main__":
    main()
