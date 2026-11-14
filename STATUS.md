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
| Gemini yorumları | ⏳ Bekliyor | `.env` > `GEMINI_API_KEY` |
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

## İlk gerçek sonuç (14 Kasım)

Doğrulama **0/4** (sınav yerleri: Hanksville %20,8 · Svalbard %2,6 · Salda %50,3 · Lut %5,5; gereken: 3'ü en iyi %1'de). Ayar yerleri: Haughton %2,3 · Holuhraun %66,1 · Yungay %74,4.

Teşhis (sadece **ayar** yerlerine bakılarak, kurala uygun):
1. **Mutlak sıcaklık** (`surface_temp_c`): Mars hedefleri −43 °C; tolerans 60 °C. Sıcak çöllerin hepsi 0 alıyor, kutuplar öne çıkıyor (Yungay +27 °C → 0). Mars sıcaklığı analog sahalarda tutturulamaz; puan yerine kopma noktası olmalı (buz sondajı hariç).
2. **ASTER mineral eşikleri** ilk tahmindi; Holuhraun'da ASTER verisi bulut yüzünden boş → mafik 0 benzerlik. Eksik veri cezası ve eşikler gözden geçirilmeli.
3. **Toz**: Mars τ ≈ 0,4-0,5; Dünya'da nadir. Tolerans/ağırlık gözden geçirilmeli.

Öne çıkan yeni aday örneği: Gale × toz testinde ilk 10 aday Taklamakan Çölü / Tarım Havzası (dünyanın büyük toz kaynaklarından).

## Karar bekleyenler

| Konu | Durum | Seçenekler |
| --- | --- | --- |
| ~~Salda'nın "fazla karbonat" cezası~~ | ✅ **Karar verildi (14 Kasım):** biyo-imza testinde karbonat tek yönlü; hedeften fazlası ceza değil (`test_profiles.yaml > biosignature > at_least`). Gerekçe: daha fazla karbonat, biyo-imzayı koruma potansiyelinin daha yüksek olması demek. Doğrulama sonucuna bakılmadan, ilke olarak verildi | Geri almak için `at_least` satırını silmek yeter |
| ASTER indeks eşikleri, kuraklık formülü | İlk tahmin (`config/grid.yaml > indices`) | Literatürden (Ninomiya indeksleri) doğrulanmalı; sınav yerlerine bakarak değiştirilmez |
| Koordinatlar | Yaklaşık | NASA kaynaklarından son kontrol |
| Oxford/MAP erişim verisi | Challenge listesinde yok | Kullanılır, sunumda NASA dışı kaynak olarak atıf yapılır (Burak'ın notu) |

## Bilinen sınırlılıklar (sunumda dürüstçe söylenecek)

- **Lav tüpleri yörüngeden görülmez.** Motor sadece tüp oluşabilecek araziyi (genç, mafik lav akıntısı) ölçer; Lanzarote bu yüzden sadece raporlanır.
- **Donmuş zemin verisi Kuzey Yarımküre'de.** ESA CCI dosyası 25°K–85°K; Güney Yarımküre'de (And dağları, Antarktika vahaları) `ground_ice = 0` sayılır.
- **Ay kutup buzu ısıl kararlılıktır, gözlem değil.** Shackleton 0,56 / Malapert 0,29 = karenin ne kadarında buz 1 m içinde kararlı olabilir (Diviner). Dünya'daki permafrost da ısıl tanım olduğu için aynı tanım seçildi.
- **Mars sıcaklık ve tozu modelden.** Mars Climate Database ölçümlerle doğrulanmış bir model; rover ölçümü değil.
- **Ay'da Dünya karşılığı olmayan değerler.** Örneğin Marius Hills'in 295 °C'lik gece-gündüz farkı; bu parametre her yerde 0 benzerlik alır ve kartta kopma olarak görünür.
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
