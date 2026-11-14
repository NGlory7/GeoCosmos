# GeoCosmos

Ay ve Mars'taki bir hedef ve test amacı için Dünya'nın tamamını NASA verisiyle tarayıp en uygun test alanlarını bulan, benzerliğin nerede koptuğunu da gösteren analog keşif aracı.

- Ne zaman, kim: [ROADMAP.md](ROADMAP.md)
- Nasıl: [ARCHITECTURE.md](ARCHITECTURE.md)
- Hangi veri, nereden: [DATA_SOURCES.md](DATA_SOURCES.md)

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
| `make data` | `python -m pipeline.build` | `frontend/public/data/` dosyalarını üretir |
| `make api` | `uvicorn api.main:app --reload` | API'yi açar (`localhost:8000`) |
| `make test` | `python -m pytest -q` | Testleri çalıştırır |
