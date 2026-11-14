# GeoCosmos — Durum

> Son güncelleme: 14 Kasım 2026. Ne hazır, ne eksik, sırada kim var. Planın kendisi [ROADMAP.md](ROADMAP.md), teknik ayrıntı [ARCHITECTURE.md](ARCHITECTURE.md), veri kaynakları [DATA_SOURCES.md](DATA_SOURCES.md).

## Tek bakışta

| Parça | Durum | Not |
| --- | --- | --- |
| Veri sözleşmesi (`core/schemas.py`, `frontend/src/types.ts`) | ✅ Hazır | Hedef, analog, `analogs/index.json`, `validation.json`, `heatmaps/index.json` |
| Skor motoru, kopma kuralları (`core/`) | ✅ Hazır | Adaylar birbirine 100 km'den yakın seçilmez |
| Earth Engine (`pipeline/ee_fetch.py`, `ee_export.py`) | ✅ Çalıştı | Hızlı yol `ee_fetch` (paralel interaktif, ~50 dk); toplu export yedek (proje başına 2 paralel görev: 6-12 saat) |
| Ham CSV → `grid.parquet` (`pipeline/features.py`) | ✅ Hazır | Maskeler, `is_new`, doğrulama kareleri, operasyon etiketleri |
| ESA CCI Permafrost (`pipeline/permafrost.py`) | ✅ Hazır | Yerel NetCDF; Earth Engine'e yükleme gerekmez |
| Keşif, doğrulama, ısı haritası, Gemini yorumu, `make data` | ✅ Hazır | Test ızgarasıyla uçtan uca denendi |
| API (`/health`, `/scenario`) | ✅ Hazır | `grid.parquet` ve Gemini anahtarı gelince canlı çalışır |
| Testler ve GitHub Actions | ✅ Hazır | Her push'ta Python testleri, "üretilen dosyalar güncel mi" kontrolü, frontend tip kontrolü ve derlemesi |
| Gerçek Dünya verisi (`grid.parquet`) | ✅ Hazır (14 Kasım) | 470 karo, 250.022 kare (60.144 maskeli), 49 dk (`pipeline.ee_fetch`). Repoda: ekibin Earth Engine'e ihtiyacı yok |
| **İlk doğrulama** | ❌ 0/4 | Teşhis ve sıradaki karar: aşağıda "Karar bekleyenler" |
| Hedef değerleri (`config/targets.yaml`) | ✅ Hazır | Mars hedefleri tüm parametreler; Ay'da sadece tanımı gereği olmayanlar boş. Üç betikle yeniden üretilebilir |
| Gemini yorumları | ✅ Hazır | Her dosyada ilk 5 aday (210 yorum, uydurma sayı kontrolünden geçti). `make data` mevcut yorumları korur, sadece yenilerini üretir |
| Üs kurulumu ve iniş alanı testi (`base_site`) | ✅ Hazır (14 Kasım) | Eğim, pürüzlülük, **aydınlanma** (yıllık ortalama öğlen güneş yüksekliği) ve buz. Ayar yeri yok, ağırlıklar önceden sabit |
| Frontend (`frontend/`) | ✅ Hazır | Giriş (Çağrı) → Ay/Mars küresi (NASA Trek mozaiği) + hedef ve test seçimi → Dünya haritası (NASA GIBS + ısı haritası + pinler) → analog kartı → senaryo kutusu; doğrulama paneli. Veri yokken her ekran "henüz çalıştırılmadı" der |
| Yayın (GitHub Pages) | ⏳ Repo ayarı bekleniyor | `.github/workflows/pages.yml` hazır; aşağıdaki "Yayın" bölümü |

Şu an `make data` sadece `targets.geojson` üretir; `grid.parquet` gelince analog, doğrulama ve ısı haritası dosyaları da otomatik üretilir.

## Baştan sona çalıştırma

Tek bir kişinin Earth Engine hesabı yeterli. `make` yoksa (Windows) parantez içindeki komutları kullanın.

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # EE_PROJECT, GEMINI_API_KEY doldurun
```

1. **Permafrost dosyası:** `ESACCI-PERMAFROST-L4-PFR-...-2023-fv05.0.nc` dosyasını `data/raw/permafrost/` altına koyun (repoya girmez, ekipten alın).
2. **Earth Engine girişi:** `earthengine authenticate`
3. **Bağlantı denemesi:** `make preview` (`python -m pipeline.ee_export --preview`). 5 satır yazdırmalı.
4. **Tüm Dünya:** `make export` (`python -m pipeline.ee_export`). 61 görev Drive > GeoCosmos klasörüne CSV yazar. Durum: <https://code.earthengine.google.com/tasks>
5. CSV'leri `data/raw/` altına indirin.
6. **Izgara:** `make grid` (`python -m pipeline.features`). Sonunda veri kapsamı yüzdeleri yazdırılır; düşük olan sütun varsa bildirin.
7. **Frontend dosyaları:** `make data` (`python -m pipeline.build`). Doğrulama sonucunu ekrana yazar.
8. `grid.parquet` 100 MB altındaysa commit'leyin, ekibin geri kalanı Earth Engine'siz çalışır.
9. **API:** `make api` (`uvicorn api.main:app --reload`).
10. **Frontend:** `cd frontend && npm ci && npm run dev` → <http://localhost:5173> (`make web`). API'yi ayrıca açın; frontend 5173, API 8000.

Tüm Dünya exportu beklenirken bölgesel deneme: `python -m pipeline.ee_export --bbox -112 37 -109 40` (Hanksville). Bölgesel sonuçlar sunumda kullanılmaz.

## Yayın

Frontend her `main` push'unda GitHub Pages'e çıkar (`.github/workflows/pages.yml`). Bir kerelik kurulum, repo sahibi:

1. GitHub > Settings > Pages > Build and deployment > Source: **GitHub Actions**
2. Settings > Secrets and variables > Actions > **Variables** > `PAGES_ENABLED` = `true`
3. Actions > "yayin" > Run workflow (ya da bir sonraki push). Adres: `https://<kullanıcı>.github.io/GeoCosmos/`

Yayında canlı API yoktur; senaryo kutusu "çevrimdışı" der, geri kalan her şey statik dosyalardan çalışır. API yayınlanırsa adresi `API_URL` değişkenine yazın.

## Yapılacaklar

| # | İş | Kim | Engel mi? |
| --- | --- | --- | --- |
| 1 | Earth Engine hesabı, `make preview`, `make export`, `make grid`, `make data` | Veri (A) | **Evet**: her şey buna bağlı |
| 2 | ~~Hedeflerin eğim ve pürüzlülüğü~~ ✅ PDS MOLA/LOLA'dan hesaplandı (`python -m pipeline.target_values --all`) | — | — |
| 3 | ~~Mars sıcaklık ve toz, Ay kutup sıcaklıkları~~ ✅ Mars Climate Database ve Diviner PRP (`pipeline.mars_climate`, `pipeline.diviner_polar`) | — | — |
| 4 | Gemini API anahtarı `.env`'e; `make data` yorumları üretir | Motor (B) | Hayır |
| 5 | İlk gerçek doğrulama sonucu; ağırlık ayarı **sadece ayar (tune) yerlerine bakarak** | A + B | — |
| 6 | 5 km yakın tarama: `data/processed/fine_scan.json` içindeki komutlar | A | Hayır (olursa iyi) |
| 7 | Burak'ın veri seti listesine eklenmeli: **MODIS MCD12Q1** (buz maskesi yedeği, NASA Earthdata), **Diviner Polar Resource Product** (`dlre_prp_south`, Ay kutup sıcaklığı ve buz), **Mars Climate Database v6.2** (Mars sıcaklık ve toz; NASA dışı, atıf gerekir). Listeden çıkabilecekler: Mars için TES/THEMIS sıcaklıkları ve SWIM (kullanılmadı) | Burak | Hayır |
| 8 | ~~Frontend ekranları~~ ✅ Hazır; Çağrı gözden geçirip görsel dile uyarlayabilir | Çağrı | Hayır |
| 9 | GitHub Pages'i aç (aşağıda) | Repo sahibi | Hayır |
| 10 | Sunum, rapor, demo videosu (`docs/`); demo senaryosu gerçek sonuçlarla son gün | Ekip | Hayır |
| 11 | Hackathon resmi kurallarını oku: önceden ne hazırlanabilir, teslim şartları | Ekip | Hayır |

`make data` her hedef × test için kaç parametrenin kullanıldığını `analogs/index.json` > `params_used` alanına yazar; eksik değerler girildikçe bu sayı artar.

## Gerçek sonuçlar ve ağırlık ayarı (14 Kasım)

Kural: ayar sadece **ayar** yerlerine bakılarak yapıldı; **sınav** yerlerine sadece en sonda, bir kez bakıldı ve sonuç değiştirilmeden kaydedildi.

| Yer | Grup | İlk çalıştırma | Ayar sonrası |
| --- | --- | --- | --- |
| Holuhraun (rover) | ayar | %66,1 | %12,0 |
| Yungay (biyo-imza → kuraklıkta korunma) | ayar | %74,4 | %23,5 → **%8,4** (bölme sonrası) |
| Haughton (buz sondajı) | ayar | %2,3 | %2,3 |
| Hanksville (rover) | **sınav** | %20,8 | %18,1 |
| Svalbard (buz sondajı) | **sınav** | %2,6 | %2,6 |
| Salda (biyo-imza → karbonat çökeli) | **sınav** | %50,3 | %83,2 → **%49,5** (bölme sonrası) |
| Lut (toz) | **sınav** | %5,5 | %5,5 |
| Lanzarote (lav tüpü) | rapor | %22,9 | %56,0 |

**Sonuç: 0/4** (ölçüt: 4 sınav yerinin 3'ü en iyi %1'de). Yapılan ayarlar (hepsi fiziksel gerekçeli, `config/` içinde gerekçeleriyle):
1. **ASTER mineral eşikleri** dünya dağılımından (yüzdelikler); eski eşiklerde karbonat %99'luk dilimdeydi, parametre fiilen ölüydü.
2. **Eksik veri** "benzemiyor" değil "bilinmiyor": ağırlık ölçülebilen parametrelere dağıtılır, kapsam %60'ın altındaysa skor kırpılır.
3. **Mutlak sıcaklık** biyo-imza puanından çıktı, kopma kutusuna `temperature` olarak girdi (buz sondajında kalıyor).
4. **Rover** ağırlıkları arazi geometrisi ve kayaç türüne kaydı; iklim ikincil.

5. **Biyo-imza ikiye bölündü** (14 Kasım, ekip kararı): "aşırı kuraklıkta korunma" (Yungay → Gale) ve "karbonat çökeli" (Salda → Jezero; karbonat + mafik/ultramafik ana kaya, serpantinleşme bağı). Gerilim veri gelmeden önce işaretlenmişti, ama bölme kararı ilk sınav sonucu görüldükten **sonra** verildi; sunumda bu açıkça söylenmeli.

Okuma: buz sondajı (Haughton, Svalbard %2-3) ve toz (Lut %5,5) en iyi %1'e yakın; rover orta; kuraklık testi (Yungay %8,4) iyileşti.

**Salda neden düşük kalıyor (ağırlık değil, çözünürlük):** Salda'nın 25 km'lik karesinde ASTER karbonat oranı 1,0003, dünya medyanının altında. Hidromanyezit kıyıda birkaç km²'lik bir şerit; karede çevre kayaç ve göl suyuyla ortalanınca sinyal kayboluyor. Doğru çözüm 5 km yakın tarama (`data/processed/fine_scan.json`), ağırlık değil. Bu sonuca bakarak **geri ayar yapılmadı**.

Öne çıkan yeni aday örneği: Gale × toz testinde ilk adaylar Taklamakan Çölü / Tarım Havzası (dünyanın büyük toz kaynaklarından).

## Karar bekleyenler

| Konu | Not |
| --- | --- |
| **Başarı ölçütü** | "En iyi %1" (~1.900 kare) 25 km'de geniş analog türleri için çok sıkı olabilir. Ölçüt değişecekse sunumda **sonuç görüldükten sonra değiştirildiği açıkça söylenmeli**; aksi halde yeni bir sınav seti gerekir |
| ~~Biyo-imzayı ikiye bölmek~~ | ✅ Bölündü (14 Kasım) |
| **Salda için 5 km yakın tarama** | Karbonat sinyali 25 km'de kayboluyor; Salda çevresinde 5 km tarama (`python -m pipeline.ee_fetch --cell-km 5 --bbox ...`) ve 5 km'lik doğrulama gerekir |

| Konu | Durum | Seçenekler |
| --- | --- | --- |
| ~~Salda'nın "fazla karbonat" cezası~~ | ✅ **Karar verildi (14 Kasım):** biyo-imza testinde karbonat tek yönlü; hedeften fazlası ceza değil (`test_profiles.yaml > biosignature > at_least`). Gerekçe: daha fazla karbonat, biyo-imzayı koruma potansiyelinin daha yüksek olması demek. Doğrulama sonucuna bakılmadan, ilke olarak verildi | Geri almak için `at_least` satırını silmek yeter |
| ASTER indeks eşikleri, kuraklık formülü | İlk tahmin (`config/grid.yaml > indices`) | Literatürden (Ninomiya indeksleri) doğrulanmalı; sınav yerlerine bakarak değiştirilmez |
| Koordinatlar | ✅ Doğrulandı (14 Kasım) | IAU/USGS Gazetteer, LROC Pits Atlas, NASA Artemis III bölgeleri; kaynaklar `config/targets.yaml` başında |
| Oxford/MAP erişim verisi | Challenge listesinde yok | Kullanılır, sunumda NASA dışı kaynak olarak atıf yapılır (Burak'ın notu) |

## Bilinen sınırlılıklar (sunumda dürüstçe söylenecek)

- **Lav tüpleri yörüngeden görülmez.** Motor sadece tüp oluşabilecek araziyi (genç, mafik lav akıntısı) ölçer; Lanzarote bu yüzden sadece raporlanır.
- **Donmuş zemin verisi Kuzey Yarımküre'de.** ESA CCI dosyası 25°K–85°K; Güney Yarımküre'de `ground_ice = 0` sayılır. Antarktika için ayrı bir ESA CCI ürünü var (60°G altı, v5.0) ama eklemek sonucu değiştirmez: 60°G altındaki 19.948 karenin hepsi buz tabakası olarak zaten maskeli (25 km'de buzsuz vahalar karede kaybolur). Gerçek boşluk And Dağları ve Patagonya'nın yüksek kesimleri (25°G–60°G arası 13.969 maskesiz kare); dağ permafrostu orada var ama küresel tutarlı bir veri yok.
- **Ay kutup buzu ısıl kararlılıktır, gözlem değil.** Shackleton 0,56 / Malapert 0,29 = karenin ne kadarında buz 1 m içinde kararlı olabilir (Diviner). Dünya'daki permafrost da ısıl tanım olduğu için aynı tanım seçildi.
- **Mars sıcaklık ve tozu modelden.** Mars Climate Database ölçümlerle doğrulanmış bir model; rover ölçümü değil.
- **Ay'da Dünya karşılığı olmayan değerler.** Örneğin Marius Hills'in 295 °C'lik gece-gündüz farkı; bu parametre her yerde 0 benzerlik alır ve kartta kopma olarak görünür.
- **Krater ayrı bir parametre değil.** Challenge kraterleri bir analog boyutu olarak sayıyor, ama Dünya'da tüm karaları kapsayan güvenilir bir krater haritası yok: kraterlerin çoğu aşınmış, gömülmüş ya da bitki altında; doğrulanmış çarpma yapıları ~200 tane ve çoğu 25 km kareden küçük. Krater arazisi motorda eğim ve pürüzlülük (topografya boyutu) üzerinden yakalanır. Bilinen krater analogları zaten tanındığı için keşif dışı listededir: Meteor Krateri ve Ries (`config/known_analogs.yaml > exclude_only`); Haughton Krateri ise buz sondajı testinin ayar yerlerinden biri. Sunumda söylenecek: "Krateri doğrudan aramıyoruz; krater benzeri araziyi eğim ve pürüzlülükle buluyoruz, bilinen kraterleri tekrar önermiyoruz."
- **Aydınlanma geometrik.** Güneş yüksekliği sadece enlemden hesaplanır; Malapert gibi tepelerin daha uzun güneş alması (yerel ufuk) hesaba katılmaz. Dünya karada en fazla ~84°K'ye çıkar (öğlen güneşi ortalama ~6°); Ay kutbunun 0–4°'si Dünya'da tam karşılanamaz.
- **Üs testinde Malapert'in ikilemi.** Malapert kadar engebeli (pürüzlülük ~470 m) yerler orta enlem dağları (Karakurum), kutup ışığına yakın yerler ise yüksek Arktik (Ellesmere, 81°K). Dünya'da ikisi bir arada yok; kartta güneş yüksekliği ✗ olarak görünür. Shackleton için ilk aday Ellesmere Adası (81,5°K).
- **Tuz düzlükleri taranıyor, tuz ölçülmüyor.** Uyuni, Atacama tuzlaları ve Ölüm Vadisi maskeli değil; kurak, düz ve çıplak arazi olarak aday olabilirler. Ama ayrı bir tuz / evaporit parametresi yok, çünkü altı hedefin hiçbiri tuz birikintisi değil. Sunumda söylenecek: "Tuz düzlükleri taramamızda var; hedeflerimiz tuz birikintisi olmadığı için ayrı tuz ölçümü eklemedik. Mars'ta klorür ya da sülfat hedefi seçilirse eklenecek ilk parametre bu (ASTER kısa dalga evaporit indeksi)."
- **Buzullar ve buz tabakaları bilerek dışarıda.** Grönland iç kesimi, Antarktika buz tabakası ve dağ buzulları (MODIS sınıf 15, kalıcı kar ve buz) tüm testlerde maskeli. `ground_ice` donmuş zemini (permafrost) ölçer, buz kütlesini değil; maskelenmeseydi Ay'ın buzlu regolitine en çok "benzeyen" yer bir buz tabakası çıkardı, bu yanlış olurdu. Buzsuz kutup arazisi (Kanada Arktik adaları, Svalbard'ın buzsuz kıyıları) taramada.
- **Madenler kapsam dışı.** Maden sahalarını gösteren küresel, tutarlı bir NASA verisi yok; hedeflerin hiçbiri madencilik ya da kaynak çıkarma testi değil (buzdan su elde etme `ice_drilling` testinde).
- **25 km çözünürlük.** Küçük sahalar (Dumont Dunes, ~30 km²) karede kaybolur; yakın tarama (5 km) bunun için.

## Yapılanlar (özet)

- Repo iskeleti, ROADMAP, ARCHITECTURE, veri sözleşmesi; challenge kaynaklarının projeye eşlenmesi (DATA_SOURCES.md, Burak'ın veri seti listesi)
- Skor motoru, kopma kuralları, test profilleri, doğrulama setinin ayar / sınav / rapor gruplarına ayrılması, keşif dışı bilinen sahalar
- SRTM yerine Copernicus DEM (60°K üstü), enleme göre gerçekten kare ızgara (Hasan), 500 m ölçek kuralı
- Earth Engine exportu, ham CSV → `grid.parquet`, buz maskesine MODIS yedeği, kıyı karesi maskesi
- Hedef değerleri ve geçmiş testler kaynaklı girildi (Hasan); eğim/pürüzlülük PDS'ten uzaktan (`target_values.py --all`), Mars iklimi (`mars_climate.py`), Ay kutbu (`diviner_polar.py`)
- Salda kararı: biyo-imzada karbonat tek yönlü benzerlik
- ESA CCI Permafrost dosyası yerelde işleniyor
- Keşif, doğrulama, ısı haritası, Gemini yorumcu (uydurma sayı kontrolüyle), `make data` uçtan uca
- `/scenario` API (Gemini tercüman, önbellek, maskeli kare filtresi, seyrek aday seçimi)
- GitHub Actions: her push'ta testler ve üretilen dosya kontrolü
- Frontend ekranları: Ay/Mars küresi (NASA Trek mozaiği), test seçimi, Dünya haritası (NASA GIBS), ısı haritası, analog kartı, senaryo kutusu, doğrulama paneli; GitHub Pages yayın iş akışı
- Halka açık Bulgular sayfası (`/bulgular`): üç yıldız aday (Taklamakan güney kenarı, Amund Ringnes Adası, Peru And Dağları), uydu görüntüsü, benzeyen/benzemeyen parametreler, Dünya'nın taklit edemedikleri, dürüst sınırlar
- Halka yönelik yazılı açıklama: [docs/halk-icin.md](docs/halk-icin.md) (yöntem, bulgular, sınav sonucu, bilerek yapmadıklarımız)
