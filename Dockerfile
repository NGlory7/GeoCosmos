# GeoCosmos canlı API (/health, /scenario). Render, Hugging Face Spaces, Railway... hepsinde aynı imaj.
# Yerelde:  docker build -t geocosmos-api . && docker run -p 8000:8000 --env-file .env geocosmos-api
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# API'nin okuduğu kod ve ayarlar; pipeline'dan sadece /scenario'nun kullandığı modüller
# (discovery: bilinen saha adları; placenames: yer adı önbelleğini okur, ağ isteği yapmaz).
# Yeni bir pipeline modülü /scenario'ya girerse buraya eklenmeli: CI'daki api-imaj işi yakalar.
COPY core/ core/
COPY api/ api/
COPY config/ config/
COPY pipeline/__init__.py pipeline/discovery.py pipeline/placenames.py pipeline/
# grid.parquet ve place_names.json commit'li: imaja girer. grid.parquet repodan çıkarılırsa
# GRID_URL'den açılışta indirilir (api/grid_source.py). Önbellek dosyaları .dockerignore'da.
COPY data/processed/ data/processed/

# Hugging Face Spaces 1000 numaralı kullanıcıyı ister; diğerlerinde de zararsız
RUN useradd -m -u 1000 app && chown -R app /app
USER app

EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
