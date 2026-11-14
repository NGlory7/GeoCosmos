"""Earth Engine export görevlerinin durumu ve Drive'daki CSV'lerin data/raw/ altına indirilmesi.

ee_export.py görevleri Drive > GeoCosmos klasörüne yazar. Bu betik aynı Earth Engine girişini
(earthengine authenticate; Drive izni girişte istenir) kullanarak:
  --status    görevlerin durumunu özetler (ÇALIŞIYOR / BİTTİ / HATA)
  (varsayılan) biten CSV'leri data/raw/ altına indirir; aynı boyuttaki dosyayı tekrar indirmez

Kullanım:
  python -m pipeline.ee_download --status
  python -m pipeline.ee_download                 # sonra: python -m pipeline.features
  python -m pipeline.ee_download --prefix bbox   # bölgesel export dosyaları
"""
from __future__ import annotations

import argparse
import io
import json
import os
from collections import Counter
from pathlib import Path

from core.profiles import load_grid_config

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


def _credentials():
    import google.auth.transport.requests
    import google.oauth2.credentials
    from ee import oauth

    path = Path(oauth.get_credentials_path())
    if not path.exists():
        raise SystemExit("Earth Engine girişi yok: earthengine authenticate")
    c = json.loads(path.read_text())
    creds = google.oauth2.credentials.Credentials(
        None, refresh_token=c["refresh_token"],
        client_id=c.get("client_id", oauth.CLIENT_ID), client_secret=c.get("client_secret", oauth.CLIENT_SECRET),
        token_uri="https://oauth2.googleapis.com/token", scopes=c.get("scopes"),
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds


def task_status(prefix: str = "grid") -> Counter:
    import ee
    from dotenv import load_dotenv

    load_dotenv()
    ee.Initialize(project=os.environ["EE_PROJECT"])
    from pipeline.ee_export import regions, task_states

    states = task_states(prefix)
    # Planlı karolar karasız olanları da içerir; sadece görevi olanlar (gönderilenler) sayılır.
    planned = {name for name, _ in regions(load_grid_config()["grid"]["coarse_km"])}
    states = {k: v for k, v in states.items() if k in planned or prefix != "grid"}
    for name, st in sorted(states.items()):
        if st == "FAILED":
            print(f"{st}: {name}")
    return Counter(states.values())


def download(prefix: str = "grid", out_dir: Path = RAW_DIR) -> list[Path]:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload

    folder = load_grid_config()["export"]["drive_folder"]
    drive = build("drive", "v3", credentials=_credentials(), cache_discovery=False)
    folders = drive.files().list(
        q=f"name = '{folder}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        fields="files(id)").execute()["files"]
    if not folders:
        raise SystemExit(f"Drive'da '{folder}' klasörü yok: export henüz bir dosya yazmamış")
    parents = " or ".join(f"'{f['id']}' in parents" for f in folders)
    files, token = [], None
    while True:
        res = drive.files().list(q=f"({parents}) and name contains '{prefix}' and trashed = false",
                                 fields="nextPageToken, files(id, name, size)", pageToken=token).execute()
        files += res["files"]
        token = res.get("nextPageToken")
        if not token:
            break
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for f in sorted(files, key=lambda f: f["name"]):
        dst = out_dir / (f["name"] if f["name"].endswith(".csv") else f["name"] + ".csv")
        if dst.exists() and str(dst.stat().st_size) == f.get("size"):
            continue
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=f["id"]))
        done = False
        while not done:
            _, done = dl.next_chunk()
        dst.write_bytes(buf.getvalue())
        written.append(dst)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="sadece görev durumunu yazdır")
    ap.add_argument("--prefix", default="grid", help="görev/dosya adı öneki (bölgesel: bbox)")
    args = ap.parse_args()
    if args.status:
        counts = task_status(args.prefix)
        print(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "görev yok")
        return
    files = download(args.prefix)
    print(f"{len(files)} dosya indirildi -> {RAW_DIR.relative_to(ROOT)}")
    print(f"toplam CSV: {len(list(RAW_DIR.glob(args.prefix + '*.csv')))}")


if __name__ == "__main__":
    main()
