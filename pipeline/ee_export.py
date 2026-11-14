"""Earth Engine -> data/raw/*.csv. Tüm karalar 25 km ızgara.

Kaynaklar (DATA_SOURCES.md): Copernicus DEM GLO-30, MODIS LST/NDVI/aylık AOD (MOD08_M3), GPM IMERG V07,
ASTER GED, MODIS arazi örtüsü (MCD12Q1, maskeler), MAP erişim süresi, SEDAC GPW nüfus; opsiyonel ESA CCI Permafrost asset'i.

Ham uydu verisi indirilmez; her şey Earth Engine'de karelere ortalanır, sadece tablo iner.
Burada sadece HAM ölçümler çıkarılır (ör. ASTER oranı, gündüz/gece LST). Parametrelere çeviri
(eşikler, kuraklık formülü, maskeler) pipeline/features.py'de yapılır; eşik değişince yeniden
export gerekmez.

Izgara (config/grid.yaml > export):
  Dünya enlem şeritlerine bölünür. Her şerit, kendi orta enleminde gerçekten kare olan
  bir projeksiyon kullanır (derece cinsinden boylam adımı 1/cos(enlem) ile genişletilir).
  Şerit genişliği, şeridin iki kenarı arasındaki doğu-batı uzama oranı max_stretch'i
  geçmeyecek kadar dar tutulur. Böylece hem 25 km'lik kareler hem 500 m'lik DEM pikselleri
  her enlemde yaklaşık kare kalır. (Tek bir küresel projeksiyon bunu sağlayamaz: örneğin
  EPSG:6933'te 79°K'de 25 km'lik "kare" ~5 km x ~117 km'lik bir şerit olur.)

Kullanım:
  earthengine authenticate                      # bir kere
  python -m pipeline.ee_export --preview        # küçük bir bölgede 5 satır yazdırır (hızlı deneme)
  python -m pipeline.ee_export --plan           # şerit planını yazdırır, Earth Engine'e bağlanmaz
  python -m pipeline.ee_export                  # tüm karalar, enlem şeritleri halinde Drive'a export
  python -m pipeline.ee_export --cell-km 5 --bbox 28 36 31 39   # yakın tarama (lon/lat kutusu)

Export bitince Drive > GeoCosmos klasöründeki CSV'leri data/raw/ altına indirin.
"""
from __future__ import annotations

import argparse
import math
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
]  # + lc_<sınıf> sütunları (masks.landcover.classes)

PREVIEW_BBOX = (29.0, 37.0, 30.5, 38.0)  # Salda çevresi
DEM_ASSET = "COPERNICUS/DEM/GLO30_2024_1"  # Copernicus DEM GLO-30 (eski COPERNICUS/DEM/GLO30 kullanımdan kalktı)

# Bir derecelik yayın yaklaşık uzunluğu (WGS84).
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON_EQ = 111_320.0
STRIPE_STEP_DEG = 0.25  # şerit kenarları bu adımın katlarına yuvarlanır

# reduceResolution tek adımda en fazla bu kadar kaynak pikseli birleştirir; aşılırsa çıktı
# pikseli SESSİZCE maskelenir. Yüksek enlemde derece tabanlı verilerin (DEM, ASTER, WorldCover)
# doğu-batı pikseli küçüldüğü için sınıra çabuk ulaşılır; bu yüzden ince veri iki adımda iner.
MAX_PIXELS = 65535


# --- Şerit planı (Earth Engine gerektirmez, test edilir) --------------------------------

def stretch(lat0: float, lat1: float) -> float:
    """Şeridin ekvatora yakın kenarı ile kutba yakın kenarı arasındaki doğu-batı uzama oranı."""
    near, far = sorted((abs(lat0), abs(lat1))) if lat0 * lat1 >= 0 else (0.0, max(abs(lat0), abs(lat1)))
    return math.cos(math.radians(near)) / math.cos(math.radians(far))


def plan_stripes(lat_lo: float, lat_hi: float, max_stretch: float, max_deg: float) -> list[tuple[float, float]]:
    """[lat_lo, lat_hi] aralığını, her birinde uzama <= max_stretch olan şeritlere böler."""
    if not lat_lo < lat_hi:
        raise ValueError("lat_lo < lat_hi olmalı")
    stripes = []
    a = lat_lo
    while a < lat_hi:
        b = min(a + STRIPE_STEP_DEG, lat_hi)  # en az bir adım: döngü her zaman ilerler
        while b < lat_hi and b - a < max_deg and stretch(a, min(b + STRIPE_STEP_DEG, lat_hi)) <= max_stretch:
            b = min(b + STRIPE_STEP_DEG, lat_hi)
        stripes.append((round(a, 4), round(b, 4)))
        a = b
    return stripes


def center_lat(lat0: float, lat1: float) -> float:
    """Kare boyutunun tam tutturulduğu enlem: şeridin ortası."""
    return (lat0 + lat1) / 2


def pixel_deg(size_m: float, lat: float) -> tuple[float, float]:
    """lat enleminde size_m x size_m karelik pikselin derece cinsinden (boylam, enlem) boyu."""
    return (size_m / (M_PER_DEG_LON_EQ * math.cos(math.radians(lat))),
            size_m / M_PER_DEG_LAT)


def stripe_name(cell_km: float, lat0: float) -> str:
    """Earth Engine görev adı: sadece harf, rakam ve . , : ; _ - kullanılabilir ('+' geçersiz)."""
    hemi = "N" if lat0 >= 0 else "S"
    return f"grid{cell_km:g}km_lat{abs(lat0):05.2f}{hemi}"


# --- Earth Engine ------------------------------------------------------------------------

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


def local_projection(size_m: float, lat: float):
    """lat enleminde size_m'lik kare pikselli coğrafi projeksiyon."""
    dx, dy = pixel_deg(size_m, lat)
    # Kuzey yukarı coğrafi ızgara: [x ölçeği, 0, x başlangıcı, 0, -y ölçeği, y başlangıcı]
    return _ee().Projection("EPSG:4326", [dx, 0, 0, 0, -dy, 0])


def _composite(collection, band: str):
    """Koleksiyon ortalaması. mean() sonucu varsayılan olarak 1° (~111 km) projeksiyon taşır ve
    reduceResolution ondan daha ince bir kareye ortalama yapamaz: komşu kareler aynı değeri alır.
    Bu yüzden kaynağın kendi projeksiyonu geri verilir."""
    return collection.select(band).mean().setDefaultProjection(collection.first().select(band).projection())


def _to_grid(img, native_m: float, mid_m: float, proj, mid_proj):
    """Ortalama ile kare çözünürlüğüne indirir.

    Ara çözünürlükten (mid_m, 500 m) ince veri önce oraya Earth Engine'in hazır ORTALAMA
    piramit katmanından iner (reproject): 30 m ya da 100 m pikseller tek tek okunmaz. Piramit
    seviyeleri 2'nin katı blok ortalamalarıdır (30 m -> ~480 m), yani "500 m'ye ortalanmış" kuralı
    korunur; okunan veri ~250 kat azalır. 500 m -> kare adımı gerçek reduceResolution ortalamasıdır."""
    ee = _ee()
    if native_m < mid_m:
        img = img.reproject(mid_proj)
    return img.reduceResolution(ee.Reducer.mean(), maxPixels=MAX_PIXELS).reproject(proj)


def build_image(cell_km: float, lat: float):
    """Tüm ham bantları, lat enleminde kare olan ızgarada tek bir görüntüde toplar."""
    ee = _ee()
    cfg = load_grid_config()
    exp, scale = cfg["export"], cfg["scale"]
    mid_m = scale["dem_resample_m"]
    proj = local_projection(cell_km * 1000, lat)
    dem_proj = local_projection(mid_m, lat)
    start, end = exp["date_range"]

    def grid(img, native_m):
        return _to_grid(img, native_m, mid_m, proj, dem_proj)

    # --- Arazi örtüsü (MODIS MCD12Q1, 500 m): maskeler ve kara oranı
    lcfg = cfg["masks"]["landcover"]
    lc = (ee.ImageCollection(lcfg["source"]).filter(ee.Filter.calendarRange(lcfg["year"], lcfg["year"], "year"))
          .first().select(lcfg["band"]))
    lc_bands = [grid(lc.eq(int(c)).rename(f"lc_{c}"), 500) for c in lcfg["classes"]]
    # Kara: su (IGBP 17) değil ve veri var (okyanus maskeli ya da 17 olabilir; ikisi de 0).
    land = lc.neq(17).unmask(0).setDefaultProjection(lc.projection())
    land_frac = grid(land, 500).rename("land_frac")

    # --- Topografya: Copernicus DEM -> 500 m (piramit ortalaması) -> eğim ve pürüzlülük -> kare ortalaması
    dem500 = ee.ImageCollection(DEM_ASSET).select("DEM").mosaic().reproject(dem_proj)
    slope = ee.Terrain.slope(dem500).rename("slope_deg")
    # Pencere piksel cinsinden: dem_proj pikselleri her enlemde ~kare olduğu için gerçek boy aynı kalır.
    radius_px = max(1, round(scale["roughness_window_km"] * 1000 / 2 / mid_m))
    rough = dem500.reduceNeighborhood(ee.Reducer.stdDev(), ee.Kernel.square(radius_px, "pixels")).rename("roughness_m")

    # --- İklim: MODIS LST (K*0.02), NDVI (*0.0001), IMERG (mm/saat), MODIS aylık AOD (*0.001)
    lst = ee.ImageCollection("MODIS/061/MOD11A2").filterDate(start, end)
    lst_day = _composite(lst, "LST_Day_1km").multiply(0.02).subtract(273.15).rename("lst_day_c")
    lst_night = _composite(lst, "LST_Night_1km").multiply(0.02).subtract(273.15).rename("lst_night_c")
    ndvi = _composite(ee.ImageCollection("MODIS/061/MOD13A2").filterDate(start, end), "NDVI") \
        .multiply(0.0001).rename("ndvi")
    precip = _composite(ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V07").filterDate(start, end),
                        "precipitation").multiply(24 * 365.25).rename("precip_mm")
    # MOD08_M3: aylık küresel 1° ürün, Dark Target + Deep Blue birleşik 550 nm (Deep Blue çölleri kapsar).
    # Günlük MAIAC granülleri (MCD19A2) on binlerce dosya demekti ve exportu saatlerce uzatıyordu.
    aod = _composite(ee.ImageCollection("MODIS/061/MOD08_M3").filterDate(start, end),
                     "AOD_550_Dark_Target_Deep_Blue_Combined_Mean_Mean").multiply(0.001).rename("aod")

    # --- Jeoloji: ASTER GED TIR emisivite -> Ninomiya oranları (ölçek katsayısı oranda sadeleşir)
    aster = ee.Image("NASA/ASTER_GED/AG100_003")
    b12, b13, b14 = (aster.select(f"emissivity_band{b}") for b in (12, 13, 14))
    aster_mi = b12.divide(b13).rename("aster_mi")
    aster_ci = b13.divide(b14).rename("aster_ci")

    # --- Donmuş zemin: ESA CCI Permafrost (opsiyonel asset). Kapsam dışı kara = 0 (permafrost yok).
    assets = [a.strip() for a in os.getenv("EE_PERMAFROST_ASSETS", "").split(",") if a.strip()]
    if assets:
        pf = ee.ImageCollection([ee.Image(a).select(0) for a in assets]).mosaic()
        # PFR yüzde (0-100) -> oran (0-1). Tercih edilen yol yerel dosyadır (pipeline/permafrost.py).
        pf = pf.unmask(0).divide(100).setDefaultProjection(ee.Image(assets[0]).projection()).rename("permafrost")
        permafrost = grid(pf, 1000)
    else:
        # Normal yol: features.py ground_ice'ı data/raw/permafrost/*.nc dosyasından yerelde hesaplar.
        permafrost = ee.Image.constant(exp["nodata"]).rename("permafrost")

    # --- Operasyon etiketleri
    access = ee.Image(cfg["ops_tags"]["road_access"]["source"]).select("accessibility").rename("access_min")
    pop = (ee.ImageCollection(cfg["ops_tags"]["remote"]["source"])
           .filter(ee.Filter.calendarRange(2020, 2020, "year")).first()
           .select("population_density").rename("pop_density"))

    bands = [
        grid(slope, mid_m), grid(rough, mid_m),
        grid(lst_day, 1000), grid(lst_night, 1000), grid(ndvi, 1000), grid(precip, 11132),
        grid(aod, 111_320), grid(aster_mi, 100), grid(aster_ci, 100), permafrost,
        grid(access, 1000), grid(pop, 1000), *lc_bands,
    ]
    data = ee.Image.cat(bands).unmask(exp["nodata"])
    lonlat = ee.Image.pixelLonLat().reproject(proj).rename(["lon", "lat"])
    # Sadece kara içeren kareler; veri boşlukları nodata ile korunur, satır düşmez.
    return ee.Image.cat([lonlat, land_frac, data]).updateMask(land_frac.gt(0)), proj


def _sample(image, proj, region):
    return image.sample(region=region, projection=proj, dropNulls=True, tileScale=4, geometries=False)


def preview(cell_km: float, bbox=PREVIEW_BBOX, n: int = 5) -> None:
    ee = _ee()
    image, proj = build_image(cell_km, center_lat(bbox[1], bbox[3]))
    rows = _sample(image, proj, ee.Geometry.Rectangle(list(bbox), None, False)).limit(n).getInfo()
    for f in rows["features"]:
        print({k: round(v, 3) if isinstance(v, float) else v for k, v in f["properties"].items()})
    print(f"{len(rows['features'])} satır (en fazla {n}).")


def regions(cell_km: float, bbox=None) -> list[tuple[str, tuple[float, float, float, float]]]:
    """(görev adı, (lon0, lat0, lon1, lat1)) listesi. bbox verilse de enlemde şeritlere bölünür.
    |enlem| > polar_lat şeritleri boylamda polar_lon_parts parçaya bölünür (2^31 piksel sınırı)."""
    cfg = load_grid_config()["export"]
    if bbox:
        lon0, lat0, lon1, lat1 = bbox
    else:
        (lat0, lat1), lon0, lon1 = cfg["lat_range"], -180, 180
    prefix = f"bbox{lon0:g}_" if bbox else ""
    max_area = float(cfg.get("max_tile_deg2", 1e9))
    out = []
    for a, b in plan_stripes(lat0, lat1, cfg["max_stretch"], cfg["max_stripe_deg"]):
        name = prefix + stripe_name(cell_km, a)
        parts = max(1, math.ceil((lon1 - lon0) * (b - a) / max_area))
        if parts == 1:
            out.append((name, (lon0, a, lon1, b)))
            continue
        step = (lon1 - lon0) / parts
        for k in range(parts):
            x0 = round(lon0 + k * step, 4)
            out.append((f"{name}_x{k + 1:02d}", (x0, a, round(x0 + step, 4), b)))
    return out


def land_regions(items: list[tuple[str, tuple[float, float, float, float]]]) -> list:
    """Kara içermeyen karoları atar: tek bir Earth Engine sorgusuyla Copernicus DEM kapsamına bakılır."""
    ee = _ee()
    land = (ee.ImageCollection(DEM_ASSET).select("DEM").mosaic().mask().gt(0)
            .unmask(0).rename("land"))
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Rectangle(list(r), None, False), {"name": n})
                               for n, r in items])
    stats = land.reduceRegions(collection=fc, reducer=ee.Reducer.max(), scale=5000, tileScale=4)
    has_land = {f["properties"]["name"] for f in stats.getInfo()["features"] if f["properties"].get("max", 0) > 0}
    return [(n, r) for n, r in items if n in has_land]


def task_states(prefix: str = "") -> dict[str, str]:
    """Görev adı -> en yeni görevin durumu (READY, RUNNING, COMPLETED, FAILED, CANCELLED)."""
    ee = _ee()
    latest: dict[str, dict] = {}
    for t in ee.data.getTaskList():
        d = t.get("description", "")
        if d.startswith(prefix) and (d not in latest or t["creation_timestamp_ms"] > latest[d]["creation_timestamp_ms"]):
            latest[d] = t
    return {d: t["state"] for d, t in latest.items()}


def export_grid(cell_km: float = 25, bbox=None, resume: bool = False) -> list:
    """Enlem şeritleri halinde Drive'a CSV export görevleri başlatır, görev listesini döndürür.
    resume=True: kuyrukta, çalışan ya da bitmiş görevi olan bölgeler atlanır (sadece eksik/hatalı)."""
    ee = _ee()
    cfg = load_grid_config()
    columns = RAW_COLUMNS + [f"lc_{c}" for c in cfg["masks"]["landcover"]["classes"]]
    active = {"READY", "RUNNING", "COMPLETED"}
    states = task_states() if resume else {}

    todo = [(n, r) for n, r in regions(cell_km, bbox) if states.get(n) not in active]
    todo = land_regions(todo) if todo else []
    print(f"{len(todo)} karo kara içeriyor ve gönderilecek")
    tasks = []
    for name, (x0, y0, x1, y1) in todo:
        image, proj = build_image(cell_km, center_lat(y0, y1))
        region = ee.Geometry.Rectangle([x0, y0, x1, y1], None, False)
        task = ee.batch.Export.table.toDrive(
            collection=_sample(image, proj, region),
            description=name, folder=cfg["export"]["drive_folder"], fileNamePrefix=name,
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
    ap.add_argument("--plan", action="store_true", help="şerit planını yazdır (Earth Engine gerekmez)")
    ap.add_argument("--resume", action="store_true", help="sadece eksik ya da hatalı görevleri başlat")
    args = ap.parse_args()
    cell_km = args.cell_km or load_grid_config()["grid"]["coarse_km"]
    bbox = tuple(args.bbox) if args.bbox else None
    if args.plan:
        for name, (_, a, _, b) in regions(cell_km, bbox):
            dx, _ = pixel_deg(cell_km * 1000, center_lat(a, b))
            print(f"{name}: {a:+.2f}..{b:+.2f}  uzama {stretch(a, b):.3f}  boylam adımı {dx:.4f}°")
        return
    init()
    if args.preview:
        preview(cell_km, bbox or PREVIEW_BBOX)
    else:
        export_grid(cell_km, bbox, resume=args.resume)


if __name__ == "__main__":
    main()
