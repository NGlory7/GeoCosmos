"""make data: frontend/public/data/ altındaki tüm dosyaları üretir.

Sıra:
  1. targets.geojson, meta.json           (her zaman; sadece config/ gerekir)
  2. analogs/<hedef>_<test>.geojson       (pipeline/discovery.py)   \
  3. validation.json                      (pipeline/validation.py)   } data/processed/grid.parquet gerekir
  4. heatmaps/<hedef>_<test>.png          (pipeline/heatmap.py)      /
  5. ai_comment alanları                  (pipeline/commentary.py; GEMINI_API_KEY gerekir)
  6. logistics.json                       (pipeline/logistics.py; yeni aday kareleri için Earth Engine gerekir,
                                           yoksa mevcut değerlerle puanlar yeniden hesaplanır)

grid.parquet yoksa 2-5 atlanır ve nasıl üretileceği yazdırılır; komut hata vermez.
grid.parquet: python -m pipeline.ee_export (Earth Engine) -> CSV'ler data/raw/ -> python -m pipeline.features

Kullanım:  python -m pipeline.build [--skip-commentary] [--skip-heatmaps] [--skip-logistics]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from core.breakdown import ALWAYS, NOTES
from core.profiles import load_grid_config, load_parameters, load_profiles, load_targets
from core.schemas import SCORE_KEYS

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "frontend" / "public" / "data"
GRID_PATH = ROOT / "data" / "processed" / "grid.parquet"


def write_targets(out_dir: Path = OUT_DIR) -> Path:
    features = []
    for t in load_targets().values():
        props = t.model_dump(exclude={"lat", "lon"})
        features.append({
            "type": "Feature",
            # Not: koordinatlar ilgili gök cismindedir (Ay/Mars), Dünya değil.
            "geometry": {"type": "Point", "coordinates": [t.lon, t.lat]},
            "properties": props,
        })
    path = out_dir / "targets.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_meta(out_dir: Path = OUT_DIR) -> Path:
    """meta.json: arayüzün göstereceği etiketler, tek kaynaktan (config + core/breakdown.py).
    Zaman damgası yok: CI "üretilen dosyalar güncel mi" kontrolü kararlı kalsın."""
    import yaml
    from core.profiles import CONFIG_DIR

    raw_tests = yaml.safe_load((CONFIG_DIR / "test_profiles.yaml").read_text(encoding="utf-8"))["tests"]
    meta = {
        "score_keys": list(SCORE_KEYS),
        "score_labels": {"topography": "Topoğrafya", "geology": "Jeoloji", "climate": "İklim"},
        "tests": [{"id": p.id, "label": p.label, "weights": p.weights, "breakdown": list(p.breakdown),
                   "at_least": list(p.at_least), "rationale": raw_tests[p.id].get("rationale", "")}
                  for p in load_profiles().values()],
        "parameters": {k: {"label": p.label, "dimension": p.dimension, "tolerance": p.tolerance,
                           "earth_source": p.earth_source} for k, p in load_parameters().items()},
        "breakdown_always": list(ALWAYS),
        "breakdown_labels": {"gravity": "Yerçekimi", "atmosphere": "Atmosfer", "radiation": "Radyasyon",
                             "liquid_water": "Sıvı su", "biology": "Biyoloji",
                             "temperature": "Sıcaklık"},
        "breakdown_notes": NOTES,
        "ops_labels": {"road_access": "Yola erişim (şehre < 6 saat)", "remote": "Issız (< 1 kişi/km²)"},
        "grid_km": load_grid_config()["grid"]["coarse_km"],
    }
    path = out_dir / "meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def build(grid_path: Path = GRID_PATH, out_dir: Path = OUT_DIR,
          commentary: bool = True, heatmaps: bool = True, fine_scan_path: Path | None = None,
          generate=None, logistics_online: bool = False) -> dict:
    from pipeline import discovery, heatmap, logistics, validation
    from pipeline import commentary as comm

    load_profiles()  # config hatalarını en başta yakala
    target_path = write_targets(out_dir)
    write_meta(out_dir)
    report: dict = {"targets": str(target_path.relative_to(ROOT) if target_path.is_relative_to(ROOT) else target_path)}
    if not grid_path.exists():
        report["grid"] = "yok"
        return report
    grid = pd.read_parquet(grid_path)
    report["grid"] = f"{len(grid)} kare"
    kept = comm.existing_comments(out_dir / "analogs")  # yeniden yazmadan önce: yorumlar silinmesin
    idx = discovery.run_discovery(grid, out_dir / "analogs")
    report["analogs"] = sum(1 for e in idx if e["file"])
    report["analogs_skipped"] = [f"{e['target_id']}/{e['test_id']}" for e in idx if not e["file"]]
    discovery.fine_scan_plan(grid, fine_scan_path or discovery.FINE_SCAN_PATH)
    res = validation.run_validation(grid)
    validation.write_validation(res, out_dir / "validation.json")
    report["validation"] = f"{res['hits']}/{res['holdout_total']} (gereken {res['min_hits']})"
    if heatmaps:
        report["heatmaps"] = len(heatmap.run_heatmaps(grid, out_dir / "heatmaps"))
    kw = {"cache_path": fine_scan_path.parent / "commentary_cache.json"} if fine_scan_path else {}
    report["commentary"] = comm.add_comments(out_dir / "analogs", generate=generate, kept=kept,
                                             allow_generate=commentary, **kw)
    report["logistics"] = logistics.run(out_dir / "analogs", out_dir / "logistics.json", online=logistics_online)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-commentary", action="store_true", help="Gemini yorumlarını üretme")
    ap.add_argument("--skip-heatmaps", action="store_true", help="PNG ısı haritalarını üretme")
    ap.add_argument("--skip-logistics", action="store_true", help="yeni aday kareleri için Earth Engine'e bağlanma")
    args = ap.parse_args()
    report = build(commentary=not args.skip_commentary, heatmaps=not args.skip_heatmaps,
                   logistics_online=not args.skip_logistics)
    for k, v in report.items():
        print(f"{k}: {v}")
    if report["grid"] == "yok":
        print("\ngrid.parquet yok: analog, doğrulama ve ısı haritası dosyaları üretilmedi.\n"
              "  1. python -m pipeline.ee_export --preview   (Earth Engine bağlantı denemesi)\n"
              "  2. python -m pipeline.ee_export             (Drive'a CSV; bitince data/raw/ altına indirin)\n"
              "  3. python -m pipeline.features              (data/raw/*.csv -> grid.parquet)\n"
              "  4. python -m pipeline.build")


if __name__ == "__main__":
    main()
