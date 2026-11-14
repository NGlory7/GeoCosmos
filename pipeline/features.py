"""data/raw/*.csv -> data/processed/grid.parquet.

Sütunlar: id, name, lat, lon, landcover + config/test_profiles.yaml > parameters anahtarları.

Ölçek ve maske kuralları config/grid.yaml'dan okunur (core.profiles.load_grid_config):
- Eğim ve pürüzlülük, SRTM önce scale.dem_resample_m (500 m) çözünürlüğe indirildikten sonra
  hesaplanır. 30 m'lik ham SRTM'den hesaplanan eğim, MOLA/LOLA hedef değerleriyle karşılaştırılamaz.
- masks.worldcover_classes sınıflarının oranı masks.max_masked_fraction'ı geçen kareler atılır;
  doğrulama setindeki yerlerin kareleri (config/known_analogs.yaml) hiçbir zaman atılmaz.
- is_new sütunu: bilinen analoglara exclude_radius_km'den uzak kareler True, yakınlar False.
"""


def build_grid() -> None:
    raise NotImplementedError("TODO")
