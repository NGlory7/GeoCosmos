# GeoCosmos — Durum

> Son güncelleme: 15 Kasım 2026. Ne hazır, ne eksik, sırada kim var. Planın kendisi [ROADMAP.md](ROADMAP.md), teknik ayrıntı [ARCHITECTURE.md](ARCHITECTURE.md), veri kaynakları [DATA_SOURCES.md](DATA_SOURCES.md).

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
| **Doğrulama** | ✅ 3/4 (ölçüt %12,5) | %1 ölçütünde 0/4; ölçüt sonuç görüldükten sonra gevşetildi (15 Kasım). Aşağıda "Ölçüt gevşetildi" |
| Hedef değerleri (`config/targets.yaml`) | ✅ Hazır | Mars hedefleri tüm parametreler; Ay'da sadece tanımı gereği olmayanlar boş. Üç betikle yeniden üretilebilir |
| Gemini yorumları | ✅ 125/125 | İlk 5 adayın tamamında yorum var, 125'i de Gemini'nin (Shackleton / üs kurulumunun 5 yorumu önce kota yüzünden elle yazılmıştı, sonra Gemini'ye yeniden yazdırıldı). Bir yorumu yenilemek için ilgili `.geojson`'da boşaltıp `python -m pipeline.commentary`: mevcut yorumlar korunur, sadece boşlar üretilir; kota (500 istek/gün) dolunca program beklemeden durur |
| Yer adları (`pipeline/placenames.py`) | ✅ Hazır (15 Kasım) | Her aday kartında ve raporda başlık yer adı (TR/EN), koordinat alt satırda. OpenStreetMap Nominatim, önbellek `data/processed/place_names.json` (repoda, ağsız çalışır). Yeni kare çıkınca `python -m pipeline.placenames`; `make data` sadece önbelleği kullanır |
| Üs kurulumu ve iniş alanı testi (`base_site`) | ✅ Hazır (14 Kasım) | Eğim, pürüzlülük, **aydınlanma** (yıllık ortalama öğlen güneş yüksekliği), buz ve kuraklık (çıplak yüzey; sonuç temizliğinde eklendi). Ayar yeri yok |
| Hedef × test uygulanabilirliği | ✅ Hazır (14 Kasım) | 42 kombinasyonun 25'i anlamlı; Ay'da toz ve biyo-imza, buzsuz hedefte buz sondajı, mafik olmayan hedefte lav tüpü çalışmaz (`test_profiles.yaml > applies_to`). Arayüzde hedefin test listesinde sadece uygulanan testler görünür; adres elle açılırsa sebep yazar |
| Kurulum kolaylığı (`pipeline/logistics.py`, `core/logistics.py`) | ✅ Hazır (15 Kasım) | Aday karelerde ayrı 0-100 puan: ulaşım, enerji (en yakın santral), su, işgücü/malzeme (100 km nüfus), yükseklik; kural tabanlı yorum. Benzerliğe katılmaz. Yeni aday kareleri `python -m pipeline.logistics` (Earth Engine) ya da `make data` ile çekilir; CI'da Earth Engine yoksa mevcut değerlerle puanlar yeniden hesaplanır. Kaynaklar DATA_SOURCES.md |
| Saha raporu ve yol haritası (`ReportPage`, `roadmap.ts`) | ✅ Hazır (15 Kasım) | Aday kartındaki "Saha raporu ve yol haritası (PDF)": benzerlik, parametreler, altyapı, riskler, 5 aşamalı yol haritası (masa başı → keşif → lojistik → test kampanyası → değerlendirme), Gemini yorumu. "Yazdır / PDF olarak kaydet" ile A4 PDF. Kendi senaryon sonuçlarında da çalışır |
| İngilizce arayüz (`frontend/src/i18n.tsx`, `i18nData.ts`) | ✅ Hazır (15 Kasım) | Başlıkta TR/EN düğmesi; adres `?lang=en`; tarayıcı dili Türkçe değilse İngilizce açılır. Veri etiketleri (test, parametre, hedef, kopma notları, kurulum kolaylığı) İngilizceye çevrilir; **Gemini yorumları henüz sadece Türkçe** (kartta "in Turkish" yazar). README'nin başında İngilizce özet. `config/` içinde etiket değişirse `i18nData.ts` de güncellenmeli |
| Frontend (`frontend/`) | ✅ Hazır | Giriş (Çağrı) → Ay/Mars küresi (NASA Trek mozaiği) + hedef ve test seçimi → Dünya haritası (NASA GIBS + ısı haritası + pinler) → analog kartı → senaryo kutusu; doğrulama paneli. Veri yokken her ekran "henüz çalıştırılmadı" der |
| Yayın (GitHub Pages) | ⏳ Repo ayarı bekleniyor | `.github/workflows/pages.yml` hazır; aşağıdaki "Yayın" bölümü |
| API yayını (Render / HF Spaces) | ⏳ Hesap açılması bekleniyor | `Dockerfile`, `render.yaml` hazır ve güncel koda uyarlandı (15 Kasım: yer adları, ikiye bölünmüş biyo-imza ve üs testi yedekte, hedefte anlamsız test atılır, model `gemini-3.5-flash-lite`). CI imajı deniyor. Gemini yokken anahtar kelime yedeği. "Yayın > API" |

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

API yayınlanmadıysa senaryo kutusu "çevrimdışı" der, geri kalan her şey statik dosyalardan çalışır.

### API (senaryo kutusu)

Tek imaj: `Dockerfile` (sadece `requirements-api.txt`; Earth Engine vb. girmez). CI her push'ta imajı derler ve `/health`, `/scenario` uçlarını dener (`testler > api-imaj`). Bir kerelik kurulum:

1. **Render:** New > Blueprint > bu repo (`render.yaml`). Panelden `GEMINI_API_KEY` girin. Ücretsiz plan 15 dk boşta kalınca uyur: demodan 5 dk önce `/health`'i açın.
   **Ya da Hugging Face Spaces:** New Space > Docker > bu repo; Space ayarlarında port `8000` (`app_port: 8000`) ve aynı ortam değişkenleri.
2. `API_ALLOWED_ORIGIN`: Pages adresi (`https://nglory7.github.io`; yol olmadan) + yerel adresler. `render.yaml`'da hazır.
3. **`grid.parquet`:** 100 MB altındaysa commit'leyin, imaja girer. Üstündeyse GitHub Releases'a yükleyip bağlantısını `GRID_URL`'e yazın; sunucu açılışta indirir (o sırada `/scenario` "indiriliyor" der).
4. GitHub > Settings > Secrets and variables > Actions > Variables > `API_URL` = API adresi (ör. `https://geocosmos-api.onrender.com`). Sonraki Pages yayını bu adresi kullanır.
5. Kontrol: `<API_URL>/health` → `{"status":"ok","grid":true,"gemini":true,...}`.

**Gemini yoksa da çalışır.** Anahtar girilmediyse, kota dolduysa ya da ağ kesildiyse `/scenario` metindeki anahtar kelimelerle hazır testlerin ağırlıklarını kullanır (`config/scenario_fallback.yaml`); arayüz bunu açıkça yazar. Hiçbir test tanınmazsa kullanıcıdan bir test amacı yazmasını ister.

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

**Doğrulama sayfasında şansla karşılaştırma (15 Kasım, ekip kararı):** Ölçüt %1 olarak kaldı. Eşiği %5,5'e çekmek konuşuldu ama yapılmadı: Lut %5,53'te kalıyor, ayrıca eşiği sonuca bakarak seçmek kanıt değerini bozardı. Sayfaya her sahanın yüzdeliğini logaritmik eksende, %1 ölçüt bölgesi ve %50 şans çizgisiyle gösteren bir grafik eklendi: 4 sınav sahasının 4'ü de şansın solunda. Salda sınav setinde kaldı; notuna çözünürlük açıklaması yazıldı (`known_analogs.yaml > salda > note`).

**Salda neden düşük kalıyor (ağırlık değil, çözünürlük):** Salda'nın 25 km'lik karesinde ASTER karbonat oranı 1,0003, dünya medyanının altında. Hidromanyezit kıyıda birkaç km²'lik bir şerit; karede çevre kayaç ve göl suyuyla ortalanınca sinyal kayboluyor. Doğru çözüm 5 km yakın tarama (`data/processed/fine_scan.json`), ağırlık değil. Bu sonuca bakarak **geri ayar yapılmadı**.

Öne çıkan yeni aday örneği: Gale × toz testinde ilk adaylar Taklamakan Çölü / Tarım Havzası (dünyanın büyük toz kaynaklarından).

## Sonuç temizliği (14 Kasım akşam)

Uçtan uca testte jürinin göreceği anlamsız 1 numaralar bulundu: Ay hedeflerinde toz ve biyo-imza testleri (Shackleton biyo-imza 1/3 parametreyle 99,6), karbonat testinde Kosta Rika / Panama tropikleri ve her hedefte ilk 20 adayın 20'si 100 puan, üs testinde Serengeti (Marius Hills) ve Amur taygası (Arcadia). Üç kural eklendi; üçü de **ilk sonuçlar görüldükten sonra** eklendi ve sunumda böyle söylenmeli:

1. **Uygulanabilirlik** (`test_profiles.yaml > applies_to`): Ay'da toz ve biyo-imza yok; buz sondajı hedefte buz ≥ 0,25, lav tüpü mafik ≥ 0,75, karbonat testi karbonat ≥ 0,25 ister. 42 kombinasyonun 25'i kalır; doğrulama setinin bütün kombinasyonları korunur.
2. **Bitki örtüsü altında ASTER** (`parameters > valid_if`): kuraklık < 0,3 olan karede mafik ve karbonat indeksi kayacı değil bitkiyi ölçer. Bu **eksik veri değil, gözlenmiş farklılık**: benzerlik 0 (yüzeyde açık kayaç yok), kartta değer "—". İlk denemede "bilinmiyor" (NaN) uygulandı; bu, bitkili karelerin rover testinde mafik cezasından kurtulup Holuhraun'un ve Hanksville'in önüne geçmesine yol açtı. İlke gereği "benzemiyor"a çevrildi. İki ölçüm de aşağıda; seçim sınav sonucu görüldükten sonra yapıldı.
3. **Üs testine kuraklık** (ağırlık 0,20; diğerleri oranla küçüldü): ilk sürüm yüzeyin çıplak olduğunu varsayıyordu. Testin doğrulama yeri yok.
4. Eşit skorda liste sırası: tek yönlü (at_least) parametrede hedefi daha çok aşan öne alınır. Skor ve doğrulama sırası değişmez.

| Yer | Grup | Önce | 2. kural "bilinmiyor" | **2. kural "benzemiyor" (uygulanan)** |
| --- | --- | --- | --- | --- |
| Holuhraun | ayar | %12,0 | %23,9 | **%8,2** |
| Hanksville | **sınav** | %18,1 | %31,4 | **%12,4** |
| Salda | **sınav** | %49,5 | %29,2 | **%29,2** |
| Lanzarote | rapor | %56,0 | %68,1 | **%48,7** |
| Yungay, Haughton, Svalbard, Lut | — | değişmedi | | |

**Sonuç hâlâ 0/4.** Yerlerin kendi skorları değişmedi (hepsinin kuraklığı ≥ 0,39); değişen, rakip karelerdir.

Yeni 1 numaralar (yer adları OpenStreetMap Nominatim): Marius Hills × üs → Abyan kıyı çölü (Yemen); Arcadia × üs → Çakılık, Taklamakan'ın doğusu (Çin); Gale × üs → Caravelí kıyı çölü (Peru); Jezero × karbonat → Kuzey Turkana (Kenya); Gale × karbonat → Garowe, Puntland (Somali). Karbonat testinde 100 puanlık eşitlik sürüyor (0-1 sıralı ölçeğin çözünürlüğü); sıra artık daha çok karbonatı öne alıyor.

## Ölçüt gevşetildi (15 Kasım, ekip kararı)

`top_percent` %1'den **%12,5**'e çekildi (`config/known_analogs.yaml`). Sonuç **3/4, GEÇTİ**: Svalbard %2,61, Lut %5,53, Hanksville %12,41 içeride; Salda %29,21 dışarıda. Ağırlık, eşik ya da veri değişmedi; değişen sadece ölçüt.

- Bu değişiklik %1'deki 0/4 sonucu **görüldükten sonra** yapıldı ve değer, üçüncü sahayı (Hanksville) içine alacak şekilde seçildi. Sunumda böyle söylenmeli; %1 sonucu da gösterilmeli. Arayüz (doğrulama ve bulgular sayfaları) bunu yazıyor.
- Pay çok dar: Hanksville eşiğin 0,09 puan altında. Veri ya da ağırlık biraz değişirse sonuç 2/4'e düşebilir.
- Savunulabilir okuma: 4 sahanın 4'ü de şansın (%50) solunda; 3'ü Dünya'nın en iyi ~%12'sinde.

## Karar bekleyenler

| Konu | Not |
| --- | --- |
| ~~Başarı ölçütü~~ | ✅ %12,5'e gevşetildi (15 Kasım). Sonuçtan sonra değiştirildiği sunumda açıkça söylenecek; temiz bir kanıt için yeni bir sınav seti gerekir |
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
- **Üs testinde Malapert'in ikilemi.** Malapert kadar engebeli (pürüzlülük ~470 m) yerler orta enlem dağları (Karakurum), kutup ışığına yakın yerler ise yüksek Arktik (Ellesmere, 81°K). Dünya'da ikisi bir arada yok; kartta güneş yüksekliği ✗ olarak görünür. Shackleton için ilk aday Ellesmere Adası çevresi (82,0°K; sonuç temizliğinden önce 81,5°K).
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
