"""grid.parquet yayındaki sunucuya nasıl gelir?

1. Repoda commit'liyse (100 MB altı) imaja zaten girer: hiçbir şey yapılmaz.
2. Değilse GRID_URL (ör. GitHub Releases bağlantısı) tanımlanır; sunucu açılışta dosyayı
   arka planda indirir. İndirme bitene kadar /scenario 503 "indiriliyor" der, /health çalışır.

İndirme önce geçici dosyaya yapılır, bitince yerine taşınır: yarım dosya hiç okunmaz.
"""
from __future__ import annotations

import logging
import os
import shutil
import threading
import urllib.request
from pathlib import Path

log = logging.getLogger("geocosmos.grid")
_thread: threading.Thread | None = None


def download(url: str, dest: Path, timeout: float = 120) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "geocosmos-api"})
    with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(dest)


def start(dest: Path, url: str | None = None) -> bool:
    """Dosya yoksa ve GRID_URL varsa arka planda indirmeyi başlatır. Başladıysa True."""
    global _thread
    url = url or os.getenv("GRID_URL")
    if dest.exists() or not url or downloading():
        return False

    def run() -> None:
        try:
            log.info("grid.parquet indiriliyor: %s", url)
            download(url, dest)
            log.info("grid.parquet hazır (%.1f MB)", dest.stat().st_size / 1e6)
        except Exception:  # ağ, 404, disk: /scenario 503 demeye devam eder
            log.exception("grid.parquet indirilemedi")

    _thread = threading.Thread(target=run, name="grid-download", daemon=True)
    _thread.start()
    return True


def downloading() -> bool:
    return _thread is not None and _thread.is_alive()
