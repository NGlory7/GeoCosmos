# GeoCosmos

**[English](#english) · [Türkçe](#türkçe)** · Live demo: <https://nglory7.github.io/GeoCosmos/> (TR/EN switch in the header; `?lang=en`)

## English

GeoCosmos is an analog-site discovery tool for NASA Space Apps 2026 (*Permanent Moon Base Locations and Mars*). For a target on the
Moon or Mars and a test purpose (rover driving, ice drilling, dust, biosignatures, lava tubes, base construction), it scans all of
Earth's land with NASA and ESA satellite data and ranks the most suitable test sites. Just as important, it shows **where the analogy
breaks**: gravity, atmosphere, radiation, liquid water and temperature differences that no place on Earth can reproduce.

- **Whole-Earth scan:** ~250,000 land cells of 25 km. Each cell carries slope and roughness (Copernicus DEM), surface temperature
  and day-night range (MODIS LST), aridity (GPM IMERG + MODIS NDVI), dust (MODIS AOD), mafic and carbonate indices (ASTER GED),
  frozen ground (ESA CCI Permafrost) and noon Sun elevation.
- **Same rules on every world:** terrain metrics for Earth, MOLA (Mars) and LOLA (Moon) are computed at the same 500 m baseline, so
  slopes are comparable.
- **Test-specific weights:** each test weights the parameters that matter to it; the weights and their rationale live in
  `config/test_profiles.yaml`.
- **New sites, not famous ones:** well-known analogs (Atacama, Haughton, Iceland, Hawaii…) are excluded from discovery and used only
  to validate the engine.
- **Honest validation:** the success criterion (3 of 4 test sites in the top 1% of Earth) was fixed in advance and is **not met
  (0/4)**. The validation page shows every site's rank against chance and the reasons (e.g. Lake Salda's carbonate strip is far
  smaller than a 25 km cell).
- **Ease of setup, site report and roadmap:** access, power, water, workforce and altitude for each candidate; a printable PDF report.
- **Gemini, strictly constrained:** it only turns a free-text scenario into weights and writes commentary from the engine's numbers;
  comments with numbers not in the engine output are rejected.

Docs: [ARCHITECTURE.md](ARCHITECTURE.md) (how), [DATA_SOURCES.md](DATA_SOURCES.md) (data), [STATUS.md](STATUS.md) (current state,
known limitations). The detailed project documents are in Turkish.

Quick start: `pip install -r requirements.txt`, then `cd frontend && npm ci && npm run dev` (precomputed results are in
`frontend/public/data/`; Earth Engine is not needed to run the interface). Commands are listed in the table below.

## Türkçe

Ay ve Mars'taki bir hedef ve test amacı için Dünya'nın tamamını NASA verisiyle tarayıp en uygun test alanlarını bulan, benzerliğin nerede koptuğunu da gösteren analog keşif aracı.

- Ne zaman, kim: [ROADMAP.md](ROADMAP.md)
- Nasıl: [ARCHITECTURE.md](ARCHITECTURE.md)
- Hangi veri, nereden: [DATA_SOURCES.md](DATA_SOURCES.md)
- **Şu an ne durumda, sırada ne var: [STATUS.md](STATUS.md)**
- **Herkes için kısa açıklama: [docs/halk-icin.md](docs/halk-icin.md)**

## Yapı

```
core/       Ortak Python paketi: veri sözleşmesi, skor motoru, kopma kuralları
pipeline/   Offline işler (Earth Engine, keşif, doğrulama, Gemini yorumları)
api/        FastAPI: /health, /scenario
config/     Hedefler, test ağırlıkları, doğrulama seti
data/       raw/ (gitignore), processed/ (grid.parquet)
frontend/   React + Leaflet; hazır sonuçlar public/data/ altında
tests/      Motor ve doğrulama testleri
```

## Başlangıç

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

| Komut | `make` yoksa | Ne yapar |
| --- | --- | --- |
| — | `python -m pipeline.ee_fetch` | **Hızlı yol:** Dünya karolarını paralel çekip `data/raw/`'a yazar (~50 dk) |
| `make preview` | `python -m pipeline.ee_export --preview` | Earth Engine'de küçük bir bölgeden 5 satır çeker (deneme) |
| — | `python -m pipeline.ee_export --plan` | Export şerit planını yazdırır (Earth Engine gerekmez) |
| `make export` | `python -m pipeline.ee_export` | Tüm karaları Drive'a CSV olarak export eder |
| — | `python -m pipeline.target_values --target <id> --dem <dosya>` | Hedefin eğim/pürüzlülüğünü Dünya ile aynı kuralla hesaplar |
| `make grid` | `python -m pipeline.features` | `data/raw/*.csv` → `data/processed/grid.parquet` |
| `make web` | `cd frontend && npm ci && npm run dev` | Arayüzü açar (`localhost:5173`) |
| `make data` | `python -m pipeline.build` | `frontend/public/data/` dosyalarını üretir |
| `make api` | `uvicorn api.main:app --reload` | API'yi açar (`localhost:8000`) |
| `make test` | `python -m pytest -q` | Testleri çalıştırır |
