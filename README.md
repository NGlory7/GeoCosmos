# GeoCosmos

Ay ve Mars'taki bir hedef ve test amacı için Dünya'nın tamamını NASA verisiyle tarayıp en uygun test alanlarını bulan, benzerliğin nerede koptuğunu da gösteren analog keşif aracı.

- Ne zaman, kim: [ROADMAP.md](ROADMAP.md)
- Nasıl: [ARCHITECTURE.md](ARCHITECTURE.md)
- Hangi veri, nereden: [DATA_SOURCES.md](DATA_SOURCES.md)
- **Şu an ne durumda, sırada ne var: [STATUS.md](STATUS.md)**

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
