# GeoCosmos

Dünya üzerindeki gezegen/uydu yüzey analoglarını bulan analiz hattı, API ve harita arayüzü.

## Yapı

```
analysis/   Python analiz hattı (Earth Engine, benzerlik, keşif, doğrulama, LLM)
api/        FastAPI: /scenario uç noktası
frontend/   Arayüz; analiz çıktıları public/data/ altında
docs/       Rapor, sunum, video
```

## Başlangıç

```bash
cp .env.example .env
pip install -r analysis/requirements.txt
python analysis/main.py
```
