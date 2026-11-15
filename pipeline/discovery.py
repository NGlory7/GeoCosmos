"""Global keşif: grid.parquet -> frontend/public/data/analogs/<hedef>_<test>.geojson.

Her hedef x test için maskeli olmayan kareler puanlanır ve en iyi discovery.top_n kare,
birbirine discovery.min_separation_km'den yakın olmayacak şekilde seçilir (config/grid.yaml).

- Bilinen sahaya yakın kareler (is_new=False) listede kalır ama "Yeni aday" sayılmaz.
- Doğrulama yerinin kendi karesi (known_id) gerçek adını ve kaynaklı geçmiş testlerini taşır.
- Hedefte bu testin hiçbir parametresi yoksa ya da test o hedefte anlamsızsa (test_profiles.yaml >
  applies_to) dosya yazılmaz, index.json'da sebebiyle görünür.
- Yakın tarama: en iyi adayların çevresi için 5 km'lik Earth Engine export kutuları
  data/processed/fine_scan.json dosyasına yazılır (python -m pipeline.ee_export --cell-km 5 --bbox ...).

Kullanım:  python -m pipeline.discovery
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from core.profiles import (load_grid_config, load_known_analogs, load_parameters, load_profiles,
                           load_targets)
from core.scoring import skip_reason, top_analogs, usable_weights
from pipeline.placenames import attach_places
from pipeline.placenames import load_cache as load_place_cache

ROOT = Path(__file__).resolve().parent.parent
GRID_PATH = ROOT / "data" / "processed" / "grid.parquet"
OUT_DIR = ROOT / "frontend" / "public" / "data" / "analogs"
FINE_SCAN_PATH = ROOT / "data" / "processed" / "fine_scan.json"
M_PER_DEG_LAT = 110_574.0


def load_grid(path: Path = GRID_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} yok. Önce: python -m pipeline.features")
    return pd.read_parquet(path)


def candidates(grid: pd.DataFrame) -> pd.DataFrame:
    """Keşifte puanlanacak kareler: maskeli olmayanlar (doğrulama kareleri maskelenmez)."""
    return grid[~grid["masked"]] if "masked" in grid else grid


def name_known_cells(analogs, grid: pd.DataFrame) -> None:
    """Doğrulama yerinin kendi karesine gerçek adını ve kaynaklı geçmiş testlerini yazar (yerinde).
    discovery ve /scenario ortak kullanır."""
    if "known_id" not in grid:
        return
    known = {a.id: a for a in load_known_analogs().analogs}
    by_cell = grid.set_index("id")["known_id"].dropna().to_dict()
    for a in analogs:
        k = by_cell.get(a.id)
        if k in known:
            a.name = known[k].name
            a.past_tests = list(known[k].past_tests)


def to_feature(analog) -> dict:
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [analog.lon, analog.lat]},
            "properties": analog.model_dump()}


def write_geojson(path: Path, features: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                               ensure_ascii=False, indent=1), encoding="utf-8")


def run_discovery(grid: pd.DataFrame | None = None, out_dir: Path = OUT_DIR) -> list[dict]:
    """Tüm hedef x test dosyalarını yazar; index kayıtlarını döndürür (analogs/index.json)."""
    grid = load_grid() if grid is None else grid
    cfg = load_grid_config()["discovery"]
    params = load_parameters()
    pool = candidates(grid)
    places = load_place_cache()  # yer adları sadece önbellekten (ağ yok): python -m pipeline.placenames
    index = []
    for target in load_targets().values():
        for profile in load_profiles().values():
            entry = {"target_id": target.id, "test_id": profile.id,
                     "file": f"{target.id}_{profile.id}.geojson"}
            reason = skip_reason(target, profile, params)
            if reason:
                index.append({**entry, "file": None, "count": 0, "reason": reason})
                continue
            used = usable_weights(profile.weights, target, params)
            analogs = top_analogs(pool, target, profile, n=cfg["top_n"], params=params,
                                  min_separation_km=cfg["min_separation_km"])
            name_known_cells(analogs, pool)
            attach_places(analogs, places)
            write_geojson(out_dir / entry["file"], [to_feature(a) for a in analogs])
            index.append({**entry, "count": len(analogs),
                          "new_count": sum(a.is_new for a in analogs),
                          "params_used": sorted(used), "params_total": len(profile.weights)})
    (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    # Artık üretilmeyen dosyalar (ör. kaldırılmış test ya da hedef) sitede eski sonuç göstermesin.
    keep = {e["file"] for e in index if e["file"]}
    for old in out_dir.glob("*.geojson"):
        if old.name not in keep:
            old.unlink()
    return index


def fine_scan_plan(grid: pd.DataFrame | None = None, out: Path = FINE_SCAN_PATH) -> list[dict]:
    """En iyi adayların çevresi için 5 km yakın tarama kutuları (çakışanlar birleştirilmez,
    aynı kare birden fazla testte çıkarsa tek kutu yazılır)."""
    grid = load_grid() if grid is None else grid
    cfg = load_grid_config()
    disc, cell_km = cfg["discovery"], cfg["grid"]["coarse_km"]
    params = load_parameters()
    pool = candidates(grid)
    half = disc["fine_scan_box_cells"] * cell_km * 1000 / 2
    boxes: dict[str, dict] = {}
    for target in load_targets().values():
        for profile in load_profiles().values():
            if skip_reason(target, profile, params):
                continue
            for a in top_analogs(pool, target, profile, n=disc["fine_scan_top"], params=params,
                                 min_separation_km=disc["min_separation_km"]):
                if a.id in boxes:
                    boxes[a.id]["for"].append(f"{target.id}/{profile.id}")
                    continue
                dy = half / M_PER_DEG_LAT
                dx = half / (111_320.0 * max(math.cos(math.radians(a.lat)), 0.05))
                bbox = [round(a.lon - dx, 3), round(a.lat - dy, 3), round(a.lon + dx, 3), round(a.lat + dy, 3)]
                boxes[a.id] = {"cell": a.id, "bbox": bbox, "for": [f"{target.id}/{profile.id}"],
                               "command": f"python -m pipeline.ee_export --cell-km {cfg['grid']['fine_km']} "
                                          f"--bbox {' '.join(map(str, bbox))}"}
    plan = list(boxes.values())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return plan


if __name__ == "__main__":
    idx = run_discovery()
    print(f"{sum(1 for e in idx if e['file'])} dosya yazıldı -> {OUT_DIR.relative_to(ROOT)}")
    for e in idx:
        if not e["file"]:
            print("atlandı:", e["target_id"], e["test_id"], "-", e["reason"])
    print(f"yakın tarama kutuları: {len(fine_scan_plan())} -> {FINE_SCAN_PATH.relative_to(ROOT)}")
