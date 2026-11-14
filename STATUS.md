# GeoCosmos — Durum

> Son güncelleme: 14 Kasım 2026. Ne hazır, ne eksik, sırada kim var. Planın kendisi [ROADMAP.md](ROADMAP.md), teknik ayrıntı [ARCHITECTURE.md](ARCHITECTURE.md), veri kaynakları [DATA_SOURCES.md](DATA_SOURCES.md).

## Tek bakışta

| Parça | Durum | Not |
| --- | --- | --- |
| Veri sözleşmesi (`core/schemas.py`, `frontend/src/types.ts`) | ✅ Hazır | Hedef, analog, `analogs/index.json`, `validation.json`, `heatmaps/index.json` |
| Skor motoru, kopma kuralları (`core/`) | ✅ Hazır | Adaylar birbirine 100 km'den yakın seçilmez |
| Earth Engine exportu (`pipeline/ee_export.py`) | 🟡 Yazıldı, **gerçek Earth Engine'de hiç çalışmadı** | İlk `make preview` küçük düzeltme gerektirebilir |
| Ham CSV → `grid.parquet` (`pipeline/features.py`) | ✅ Hazır | Maskeler, `is_new`, doğrulama kareleri, operasyon etiketleri |
| ESA CCI Permafrost (`pipeline/permafrost.py`) | ✅ Hazır | Yerel NetCDF; Earth Engine'e yükleme gerekmez |
| Keşif, doğrulama, ısı haritası, Gemini yorumu, `make data` | ✅ Hazır | Test ızgarasıyla uçtan uca denendi |
| API (`/health`, `/scenario`) | ✅ Hazır | `grid.parquet` ve Gemini anahtarı gelince canlı çalışır |
| Testler ve GitHub Actions | ✅ Hazır | Her push'ta testler + "üretilen dosyalar güncel mi" kontrolü |
| **Gerçek Dünya verisi (`grid.parquet`)** | ❌ Yok | Earth Engine hesabı bekleniyor; **asıl engel bu** |
| Hedef değerleri (`config/targets.yaml`) | 🟡 Kısmi | Mineral, buz, kuraklık var; eğim, sıcaklık, toz eksik |
| Gemini yorumları | ⏳ Bekliyor | `.env` > `GEMINI_API_KEY` |
| Frontend | 👤 Çağrı | Bu belgenin kapsamı dışında; sözleşme yukarıda |

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

Tüm Dünya exportu beklenirken bölgesel deneme: `python -m pipeline.ee_export --bbox -112 37 -109 40` (Hanksville). Bölgesel sonuçlar sunumda kullanılmaz.

## Yapılacaklar

| # | İş | Kim | Engel mi? |
| --- | --- | --- | --- |
| 1 | Earth Engine hesabı, `make preview`, `make export`, `make grid`, `make data` | Veri (A) | **Evet**: her şey buna bağlı |
| 2 | Hedeflerin eğim ve pürüzlülüğü: MOLA MEGDR ve LOLA DEM'lerini PDS'ten indirip `python -m pipeline.target_values --target <id> --dem <dosya>` | Veri (A) | Evet: şu an her test 1–4 parametreyle puanlanıyor |
| 3 | Mars hedeflerinin sıcaklık ve toz değerleri (TES / THEMIS / Mars Climate Database), Ay kutup hedeflerinin sıcaklıkları (Diviner) | Veri (A) | Evet: aynı sebep |
| 4 | Gemini API anahtarı `.env`'e; `make data` yorumları üretir | Motor (B) | Hayır |
| 5 | İlk gerçek doğrulama sonucu; ağırlık ayarı **sadece ayar (tune) yerlerine bakarak** | A + B | — |
| 6 | 5 km yakın tarama: `data/processed/fine_scan.json` içindeki komutlar | A | Hayır (olursa iyi) |
| 7 | Burak'ın veri seti listesine MODIS MCD12Q1 (buz maskesi yedeği) eklenmeli | Burak | Hayır |
| 8 | Frontend: [ARCHITECTURE.md > Veri sözleşmesi](ARCHITECTURE.md#veri-sözleşmesi) ve `frontend/src/types.ts` | Çağrı | — |

`make data` her hedef × test için kaç parametrenin kullanıldığını `analogs/index.json` > `params_used` alanına yazar; eksik değerler girildikçe bu sayı artar.

## Karar bekleyenler

| Konu | Durum | Seçenekler |
| --- | --- | --- |
| **Salda'nın "fazla karbonat" cezası** | Jezero karbonatı 0,5 girildi; daha zengin olan Salda (sınav yeri) bu yüzden puan kaybediyor | (a) Karbonat için "hedeften fazlası da tam puan" kuralı, (b) Jezero değerini yeniden değerlendirmek. Salda sınav yeri olduğu için karar ilke olarak verilmeli, sonuca bakarak değil |
| ASTER indeks eşikleri, kuraklık formülü | İlk tahmin (`config/grid.yaml > indices`) | Literatürden (Ninomiya indeksleri) doğrulanmalı; sınav yerlerine bakarak değiştirilmez |
| Koordinatlar | Yaklaşık | NASA kaynaklarından son kontrol |
| Oxford/MAP erişim verisi | Challenge listesinde yok | Kullanılır, sunumda NASA dışı kaynak olarak atıf yapılır (Burak'ın notu) |

## Bilinen sınırlılıklar (sunumda dürüstçe söylenecek)

- **Lav tüpleri yörüngeden görülmez.** Motor sadece tüp oluşabilecek araziyi (genç, mafik lav akıntısı) ölçer; Lanzarote bu yüzden sadece raporlanır.
- **Donmuş zemin verisi Kuzey Yarımküre'de.** ESA CCI dosyası 25°K–85°K; Güney Yarımküre'de (And dağları, Antarktika vahaları) `ground_ice = 0` sayılır.
- **Ay'da Dünya karşılığı olmayan değerler.** Örneğin Marius Hills'in 295 °C'lik gece-gündüz farkı; bu parametre her yerde 0 benzerlik alır ve kartta kopma olarak görünür.
- **25 km çözünürlük.** Küçük sahalar (Dumont Dunes, ~30 km²) karede kaybolur; yakın tarama (5 km) bunun için.

## Yapılanlar (özet)

- Repo iskeleti, ROADMAP, ARCHITECTURE, veri sözleşmesi; challenge kaynaklarının projeye eşlenmesi (DATA_SOURCES.md, Burak'ın veri seti listesi)
- Skor motoru, kopma kuralları, test profilleri, doğrulama setinin ayar / sınav / rapor gruplarına ayrılması, keşif dışı bilinen sahalar
- SRTM yerine Copernicus DEM (60°K üstü), enleme göre gerçekten kare ızgara (Hasan), 500 m ölçek kuralı
- Earth Engine exportu, ham CSV → `grid.parquet`, buz maskesine MODIS yedeği, kıyı karesi maskesi
- Hedef değerleri (kısmi) ve geçmiş testler kaynaklı girildi (Hasan); Mars/Ay DEM hesabı (`target_values.py`)
- ESA CCI Permafrost dosyası yerelde işleniyor
- Keşif, doğrulama, ısı haritası, Gemini yorumcu (uydurma sayı kontrolüyle), `make data` uçtan uca
- `/scenario` API (Gemini tercüman, önbellek, maskeli kare filtresi, seyrek aday seçimi)
- GitHub Actions: her push'ta testler ve üretilen dosya kontrolü
