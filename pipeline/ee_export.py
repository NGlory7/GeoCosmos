"""Earth Engine -> data/raw/*.csv. Tüm karalar 25 km ızgara.

Kaynaklar (DATA_SOURCES.md): Copernicus DEM GLO-30, MODIS LST/NDVI/MAIAC AOD, GPM IMERG V07,
ASTER GED, ESA WorldCover, MAP erişim süresi, SEDAC GPW nüfus; opsiyonel ESA CCI Permafrost asset'i.

Ham uydu verisi indirilmez; her şey Earth Engine'de karelere ortalanır, sadece tablo iner.
Burada sadece HAM ölçümler çıkarılır (ör. ASTER oranı, gündüz/gece LST). Parametrelere çeviri
(eşikler, kuraklık formülü, maskeler) pipeline/features.py'de yapılır; eşik değişince yeniden
export gerekmez.

Kullanım:
  earthengine authenticate                      # bir kere
  python -m pipeline.ee_export --preview        # küçük bir bölgede 5 satır yazdırır (hızlı deneme)
  python -m pipeline.ee_export                  # tüm karalar, enlem şeritleri halinde Drive'a export
  python -m pipeline.ee_export --cell-km 5 --bbox 28 36 31 39   # yakın tarama (lon/lat kutusu)

Export bitince Drive > GeoCosmos klasöründeki CSV'leri data/raw/ altına indirin.
"""
from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from core.profiles import load_grid_config

# CSV sütunları (features.py bu adları bekler).
RAW_COLUMNS = [
    "lon", "lat", "land_frac",
    "slope_deg", "roughness_m",
    "lst_day_c", "lst_night_c", "ndvi", "precip_mm", "aod",
    "aster_mi", "aster_ci", "permafrost",
    "access_min", "pop_density",
]  # + wc_<sınıf> sütunları (masks.worldcover_classes)

PREVIEW_BBOX = (29.0, 37.0, 30.5, 38.0)  # Salda çevresi


def _ee():
    import ee  # sadece gerektiğinde yükle: testler Earth Engine olmadan çalışır
    return ee


def init() -> None:
    ee = _ee()
    load_dotenv()
    project = os.getenv("EE_PROJECT")
    if not project:
        raise SystemExit(".env > EE_PROJECT tanımlı değil (Earth Engine bulut proje kimliği).")
    ee.Initialize(project=project)


def _to_grid(img, native_m: float, target_m: float, proj, mid_proj):
    """Ortalama ile kare çözünürlüğüne indirir. Çok ince veri (WorldCover 10 m) iki adımda iner,
    çünkü reduceResolution tek adımda en fazla 65 535 pikseli birleştirebilir."""
    ee = _ee()
    if (target_m / native_m) ** 2 > 65535:
        img = img.reduceResolution(ee.Reducer.mean(), maxPixels=65535).reproject(mid_proj)
    return img.reduceResolution(ee.Reducer.mean(), maxPixels=65535).reproject(proj)


def build_image(cell_km: float):
    """Tüm ham bantları kare çözünürlüğünde tek bir görüntüde toplar."""
    ee = _ee()
    cfg = load_grid_config()
    exp, scale = cfg["export"], cfg["scale"]
    crs = exp["projection"]
    proj = ee.Projection(crs).atScale(cell_km * 1000)
    dem_proj = ee.Projection(crs).atScale(scale["dem_resample_m"])
    start, end = exp["date_range"]
    aod_start, aod_end = exp["aod_date_range"]

    def grid(img, native_m):
        return _to_grid(img, native_m, cell_km * 1000, proj, dem_proj)

    # --- Topografya: Copernicus DEM -> 500 m -> eğim ve pürüzlülük -> kare ortalaması
    dem30 = (ee.ImageCollection("COPERNICUS/DEM/GLO30").select("DEM").mosaic()
             .setDefaultProjection("EPSG:4326", None, 30))
    dem500 = dem30.reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(dem_proj)
    slope = ee.Terrain.slope(dem500).rename("slope_deg")
    rough = dem500.reduceNeighborhood(
        ee.Reducer.stdDev(),
        ee.Kernel.square(scale["roughness_window_km"] * 500, "meters"),
    ).rename("roughness_m")
    land = dem30.mask().gt(0).unmask(0).setDefaultProjection("EPSG:4326", None, 30)
    land_frac = grid(land.reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(dem_proj),
                     scale["dem_resample_m"]).rename("land_frac")

    # --- İklim: MODIS LST (K*0.02), NDVI (*0.0001), IMERG (mm/saat), MAIAC AOD (*0.001)
    lst = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(start, end)
    lst_day = lst.select("LST_Day_1km").mean().multiply(0.02).subtract(273.15).rename("lst_day_c")
    lst_night = lst.select("LST_Night_1km").mean().multiply(0.02).subtract(273.15).rename("lst_night_c")
    ndvi = (ee.ImageCollection("MODIS/061/MOD13A2").filterDate(start, end)
            .select("NDVI").mean().multiply(0.0001).rename("ndvi"))
    precip = (ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V07").filterDate(start, end)
              .select("precipitation").mean().multiply(24 * 365.25).rename("precip_mm"))
    aod = (ee.ImageCollection("MODIS/061/MCD19A2_GRANULES").filterDate(aod_start, aod_end)
           .select("Optical_Depth_055").mean().multiply(0.001).rename("aod"))

    # --- Jeoloji: ASTER GED TIR emisivite -> Ninomiya oranları (ölçek katsayısı oranda sadeleşir)
    aster = ee.Image("NASA/ASTER_GED/AG100_003")
    b12, b13, b14 = (aster.select(f"emissivity_band{b}") for b in (12, 13, 14))
    aster_mi = b12.divide(b13).rename("aster_mi")
    aster_ci = b13.divide(b14).rename("aster_ci")

    # --- Donmuş zemin: ESA CCI Permafrost (opsiyonel asset). Kapsam dışı kara = 0 (permafrost yok).
    assets = [a.strip() for a in os.getenv("EE_PERMAFROST_ASSETS", "").split(",") if a.strip()]
    if assets:
        pf = ee.ImageCollection([ee.Image(a).select(0) for a in assets]).mosaic()
        pf = pf.unmask(0).setDefaultProjection(ee.Image(assets[0]).projection()).rename("permafrost")
        permafrost = grid(pf, 1000)
    else:
        print("UYARI: EE_PERMAFROST_ASSETS yok; permafrost sütunu boş kalacak (ground_ice NaN).")
        permafrost = ee.Image.constant(exp["nodata"]).rename("permafrost")

    # --- Maskeler: WorldCover sınıf oranları (10 m -> 500 m -> kare)
    wc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    wc_bands = [grid(wc.eq(int(c)).rename(f"wc_{c}"), 10) for c in cfg["masks"]["worldcover_classes"]]

    # --- Operasyon etiketleri
    access = ee.Image(cfg["ops_tags"]["road_access"]["source"]).select("accessibility").rename("access_min")
    pop = (ee.ImageCollection(cfg["ops_tags"]["remote"]["source"])
           .filter(ee.Filter.calendarRange(2020, 2020, "year")).first()
           .select("population_density").rename("pop_density"))

    bands = [
        grid(slope, scale["dem_resample_m"]), grid(rough, scale["dem_resample_m"]),
        grid(lst_day, 1000), grid(lst_night, 1000), grid(ndvi, 1000), grid(precip, 11132),
        grid(aod, 1000), grid(aster_mi, 100), grid(aster_ci, 100), permafrost,
        grid(access, 1000), grid(pop, 1000), *wc_bands,
    ]
    data = ee.Image.cat(bands).unmask(exp["nodata"])
    lonlat = ee.Image.pixelLonLat().reproject(proj).rename(["lon", "lat"])
    # Sadece kara içeren kareler; veri boşlukları nodata ile korunur, satır düşmez.
    return ee.Image.cat([lonlat, land_frac, data]).updateMask(land_frac.gt(0)), proj


def _sample(image, proj, region):
    return image.sample(region=region, projection=proj, dropNulls=True, tileScale=4, geometries=False)


def preview(cell_km: float, bbox=PREVIEW_BBOX, n: int = 5) -> None:
    ee = _ee()
    image, proj = build_image(cell_km)
    rows = _sample(image, proj, ee.Geometry.Rectangle(list(bbox), None, False)).limit(n).getInfo()
    for f in rows["features"]:
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in f["properties"].items()})
    print(f"{len(rows['features'])} satır (en fazla {n}).")


def export_grid(cell_km: float = 25, bbox=None) -> list:
    """Enlem şeritleri halinde Drive'a CSV export görevleri başlatır, görev listesini döndürür."""
    ee = _ee()
    cfg = load_grid_config()["export"]
    image, proj = build_image(cell_km)
    columns = RAW_COLUMNS + [f"wc_{c}" for c in load_grid_config()["masks"]["worldcover_classes"]]

    if bbox:
        regions = [(f"bbox_{cell_km:g}km", bbox)]
    else:
        lo, hi = cfg["lat_range"]
        step = cfg["stripe_deg"]
        regions = [(f"grid{cell_km:g}km_lat{lat:+03d}", (-180, lat, 180, min(lat + step, hi)))
                   for lat in range(lo, hi, step)]

    tasks = []
    for name, (x0, y0, x1, y1) in regions:
        region = ee.Geometry.Rectangle([x0, y0, x1, y1], None, False)
        task = ee.batch.Export.table.toDrive(
            collection=_sample(image, proj, region),
            description=name, folder=cfg["drive_folder"], fileNamePrefix=name,
            fileFormat="CSV", selectors=columns,
        )
        task.start()
        tasks.append(task)
        print("başlatıldı:", name)
    print("Durum: https://code.earthengine.google.com/tasks  (ya da: earthengine task list)")
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cell-km", type=float, default=None, help="kare boyu (varsayılan grid.yaml > coarse_km)")
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--preview", action="store_true", help="küçük bölgede birkaç satır yazdır, export etme")
    args = ap.parse_args()
    cell_km = args.cell_km or load_grid_config()["grid"]["coarse_km"]
    init()
    if args.preview:
        preview(cell_km, tuple(args.bbox) if args.bbox else PREVIEW_BBOX)
    else:
        export_grid(cell_km, tuple(args.bbox) if args.bbox else None)


if __name__ == "__main__":
    main()
