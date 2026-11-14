"""GeoCosmos analiz hattı.

Çıktıları frontend/public/data/ altına yazar:
targets.geojson, analogs_*.geojson, discovery.geojson, validation.json
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT.parent / "frontend" / "public" / "data"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # TODO: processing -> similarity -> discovery -> validation -> llm


if __name__ == "__main__":
    main()
