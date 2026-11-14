# GeoCosmos — Veri Kaynakları

> Her parametrenin Dünya, Mars ve Ay tarafında hangi veriden geldiği, nasıl hesaplandığı ve nerede eksik kaldığı. Parametre tanımları: `config/test_profiles.yaml`. Hesaplama kuralları: `config/grid.yaml`.

**Kural:** Her sayının bir kaynağı var. Elle girilen değerler `"source": "elle — <makale/link>"` etiketi taşır. Challenge kaynak listesindeki NASA dışı siteler için o sitenin veri kullanım koşullarına uyulur ve atıf yapılır.

## Challenge kaynakları nerede kullanılıyor

| Kaynak | Ne için | Nasıl erişiyoruz |
| --- | --- | --- |
| **NASA Earthdata Search** | MODIS (LST, NDVI, MAIAC AOD, MCD12Q1 buz maskesi), GPM IMERG, ASTER GED, EMIT, SEDAC ürünlerinin resmi kaynağı ve atıfı | Hesaplama Earth Engine'deki aynı ürünlerle; DOI ve atıf Earthdata'dan |
| **NASA Worldview** | Keşif adaylarının elle kontrolü (aşama 4), sunum görselleri | Tarayıcı; MODIS/VIIRS gerçek renk, AOD, kar örtüsü katmanları |
| **NASA PDS** | Mars hedef değerleri: MOLA (eğim, pürüzlülük), TES (sıcaklık, toz opaklığı, mineral), THEMIS, CRISM (karbonat/kil) | PDS Geosciences Node ürünleri; gerektiğinde Mars Trek üzerinden görsel |
| **NASA LRO (LOLA, LEND, Mini-RF, LROC)** | Ay hedef değerleri: LOLA eğim/pürüzlülük, LEND hidrojen (buz), Mini-RF radar (pürüzlülük/buz) | PDS Geosciences Node LRO sayfası |
| **NASA LRO Diviner** | Ay yüzey sıcaklığı; Shackleton ve Malapert için yıllık ortalama sıcaklık ve buz kararlılık derinliği | Polar Resource Product (`dlre_prp_south.tab`); `pipeline/diviner_polar.py` sadece hedef karesinin satırlarını HTTP aralık isteğiyle okur |
| **ESA Copernicus Data Space** | Copernicus DEM GLO-30 (Dünya eğimi, SRTM'nin yerine); Sentinel-2 görüntüsü (aşama 4); Sentinel-1 SAR (opsiyonel) | Earth Engine'deki kopyası (`COPERNICUS/DEM/GLO30`, `COPERNICUS/S2_SR_HARMONIZED`, `COPERNICUS/S1_GRD`) |
| **ESA Open Science Catalog** | ESA CCI Permafrost (donmuş zemin), ESA WorldCover (maske) | CCI: CEDA'dan NetCDF (v5.0, 2023, Kuzey Yarımküre) `data/raw/permafrost/` altına konur, `pipeline/permafrost.py` yerelde ızgaraya ortalar; WorldCover: `ESA/WorldCover/v200` |
| **JAXA G-Portal** | GSMaP yağış (IMERG ile çapraz kontrol); GCOM-C SGLI yüzey sıcaklığı (opsiyonel kontrol) | GSMaP Earth Engine'de (`JAXA/GPM_L3/GSMaP/v8/operational`); SGLI G-Portal'dan |
| **CSA RADARSAT-1 / RCM** | Lav akıntısı adaylarında yüzey dokusunun radar ile elle kontrolü; Ay Mini-RF ile görsel karşılaştırma | CSA açık veri portalı; işleme için CSA SAR Python eğitimi |

## Parametreler

Tüm Dünya değerleri 25 km'lik (yakın taramada 5 km) karelere ortalanır. Mars ve Ay hedefleri için her parametre tek değerdir.

| Parametre | Dünya | Mars | Ay | Ölçek / birim |
| --- | --- | --- | --- | --- |
| `slope_deg` | Copernicus DEM GLO-30 → 500 m'ye ortalanır → eğim | MOLA MEGDR (463 m) → 500 m | LOLA (kutup 80 m, ekvator 237 m) → 500 m | Derece |
| `roughness_m` | Aynı 500 m DEM, 5 km pencerede std | MOLA, aynı kural | LOLA, aynı kural | Metre |
| `surface_temp_c` | MODIS LST (MOD11A2), gündüz+gece yıllık ortalama | Mars Climate Database v6.2, yerel saat 10:30/22:30, 12 mevsim | Kutup: Diviner PRP yıllık ortalama; ekvator: Diviner (Williams et al. 2017) | °C |
| `temp_range_c` | MODIS LST, gündüz − gece yıllık ortalama | Mars Climate Database v6.2, aynı saatler | Ekvator: Diviner (Williams et al. 2017); kutup: yok (PRP'de en düşük sıcaklık yok) | °C |
| `aridity` | GPM IMERG V07 yıllık yağış + MODIS NDVI (MOD13A2); formül `grid.yaml > indices` | Sabit 1,0 | Sabit 1,0 | 0–1 |
| `dust_aod` | MODIS MAIAC AOD 550 nm (MCD19A2), yıllık ortalama | Mars Climate Database v6.2, görünür sütun toz optik derinliği, 12 mevsim | Değer yok (atmosfer yok) → parametre atılır | Optik derinlik |
| `mafic_index` | ASTER GED (AG100) TIR emisivite → Ninomiya mafik indeks → 0–1 | TES / CRISM, elle 0–1 | LROC / Lunar Prospector, elle 0–1 (mare bazalt yüksek) | 0–1 sıralı |
| `carbonate_index` | ASTER GED TIR → Ninomiya karbonat indeks → 0–1 | CRISM tespitleri, elle 0–1 | Sabit 0 | 0–1 sıralı |
| `ground_ice` | ESA CCI Permafrost PFR (yüzde → oran, 0,01°, 25°K–85°K; yerelde `pipeline/permafrost.py`) | SHARAD / SWIM / Odyssey, elle 0–1 | Kutup: Diviner PRP, buzun 1 m içinde ısıl olarak kararlı olduğu alan oranı; ekvator: Lunar Prospector, elle | 0–1 oran |

### 0–1 sıralı ölçek

Dünya'daki indeksler (ör. ASTER oranları) ile Mars/Ay makale bulguları aynı birimde değildir. Bu yüzden ikisi de aynı 0–1 basamaklarına çevrilir:

| Değer | Anlamı |
| --- | --- |
| 0 | Yok / tespit edilmemiş |
| 0,25 | İz düzeyinde |
| 0,5 | Belirgin ama baskın değil |
| 0,75 | Baskın |
| 1 | Neredeyse tamamen |

Dünya tarafında indeks → basamak eşikleri `config/grid.yaml > indices` bölümündedir; Mars/Ay değeri yazılırken kaynakta hangi basamağa karşılık geldiği not edilir.

### Hedef değerlerini yeniden üretmek

| Değerler | Komut | Kaynak |
| --- | --- | --- |
| 6 hedefin `slope_deg`, `roughness_m` | `python -m pipeline.target_values --all` | PDS MOLA MEGDR, LOLA LDEM (uzaktan okuma, indirme yok) |
| Mars `surface_temp_c`, `temp_range_c`, `dust_aod` | `python -m pipeline.mars_climate` | Mars Climate Database v6.2 web arayüzü |
| Shackleton, Malapert `surface_temp_c`, `ground_ice` | `python -m pipeline.diviner_polar` | PDS Diviner Polar Resource Product |

Komutlar `config/targets.yaml`'a yapıştırılacak satırları yazdırır; dosyayı kendileri değiştirmez.

**Mars Climate Database** challenge listesinde değil (LMD/ESA/CNES): TES, MCS ve rover ölçümleriyle doğrulanmış bir iklim modeli. Üç Mars hedefini tek ve tutarlı bir kaynaktan, Dünya'daki MODIS geçiş saatleriyle aynı yerel saatlerde verdiği için seçildi. Sunumda NASA dışı kaynak olarak atıf yapılır (Millour et al., MCD v6).

## Operasyon etiketleri (puan değil)

| Etiket | Kaynak | Kural |
| --- | --- | --- |
| `road_access` | Malaria Atlas Project şehirlere erişim süresi (`Oxford/MAP/accessibility_to_cities_2015_v1_0`) | Kare ortalaması < 6 saat |
| `remote` | NASA SEDAC GPWv4.11 nüfus yoğunluğu (`CIESIN/GPWv411/GPW_Population_Density`) | < 1 kişi/km² |

Kartta ✓/✗ olarak gösterilir, skora girmez.

## Bilinen kapsam boşlukları

| Veri | Boşluk | Çözüm |
| --- | --- | --- |
| SRTM | Sadece 60°K–56°G; Haughton ve Svalbard dışarıda | **Kullanılmıyor**, yerine küresel Copernicus DEM |
| EMIT | Sadece ~52°K–52°G ve kurak bölgeler | Skora girmez; aşama 4'te ve kartta ek kanıt olarak gösterilir |
| ASTER GED | 2000–2008 açık hava pikselleri; bulutlu tropiklerde boşluk | Eksik kare 0 benzerlik alır (`core/scoring.py`) |
| MODIS AOD | Kar/buz üzerinde yok | Eksik kare 0 benzerlik alır |
| ESA CCI Permafrost | Sadece Kuzey Yarımküre (25°K–85°K); permafrost olmayan kara NaN | NaN ve kapsam dışı = 0. Güney Yarımküre (And dağları, Antarktika vahaları) 0 sayılır: bilinen sınırlılık |
| ESA WorldCover | Antarktika kapsamı doğrulanamadı | Buz maskesi `max(WorldCover buz, MODIS MCD12Q1 buz)`; MODIS küresel (`grid.yaml > masks > ice_fallback`) |
| Kıyı ve ada kareleri | Değerler küçük bir kara parçasından gelir | Kara oranı %50'nin altındaysa kare maskelenir (`min_land_fraction`); doğrulama kareleri hariç |
| Ay `dust_aod` | Atmosfer yok, değer tanımsız | Hedefte yazılmaz, motor ağırlığı diğerlerine dağıtır |

## Hesaplar ve erişim

- [ ] NASA Earthdata Login (Earthdata Search, LP DAAC, GES DISC)
- [ ] Google Earth Engine (proje kimliği `.env` > `EE_PROJECT`)
- [ ] Copernicus Data Space (Sentinel görüntüleri doğrudan indirilecekse)
- [x] ESA CCI Permafrost dosyası indirildi (CEDA); repoya girmez, ekipte elden dağıtılır
- [ ] JAXA G-Portal (sadece SGLI kontrolü yapılacaksa)
- [ ] Gemini API anahtarı
