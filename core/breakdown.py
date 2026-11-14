"""Kopma kuralları: benzerliğin Dünya'da hiçbir yerde sağlanamadığı noktalar.

Bunlar puana girmez; analog kartındaki "kopma kutusu"nda gösterilir.
"""
from __future__ import annotations

from core.profiles import TestProfile
from core.schemas import Body

# Her gök cismi için Dünya'dan temel farklar (kartta açıklama olarak gösterilir).
NOTES: dict[str, dict[str, str]] = {
    "moon": {
        "gravity": "Yerçekimi Dünya'nın ~1/6'sı (1,62 m/s²); toz ve tekerlek davranışı farklı.",
        "atmosphere": "Atmosfer yok denecek kadar ince; rüzgar aşınması ve ısı taşınımı yok.",
        "radiation": "Manyetik alan ve atmosfer koruması yok; yüzey doğrudan kozmik ışına açık.",
        "liquid_water": "Yüzeyde sıvı su yok; buz sadece kalıcı gölgelerde.",
        "biology": "Bilinen bir biyolojik süreç yok; Dünya'daki her sahada mikrobiyal yaşam var.",
    },
    "mars": {
        "gravity": "Yerçekimi Dünya'nın ~%38'i (3,71 m/s²).",
        "atmosphere": "Atmosfer çok ince (~%0,6) ve çoğunlukla CO₂; toz taşınımı farklı işler.",
        "radiation": "Küresel manyetik alan yok; yüzey radyasyonu Dünya'dan çok yüksek.",
        "liquid_water": "Bugün yüzeyde kalıcı sıvı su yok; Dünya sahalarında su döngüsü sürüyor.",
        "biology": "Dünya sahalarında modern yaşam var; biyo-imza testinde kirlilik riski yaratır.",
    },
}

# Her hedef için her zaman kopan farklar (test amacından bağımsız).
ALWAYS: tuple[str, ...] = ("gravity",)


def breakdown_for(body: Body, profile: TestProfile) -> list[str]:
    """Bu hedef + test için gösterilecek kopma anahtarları (sıralı, tekrarsız)."""
    keys = list(ALWAYS) + [k for k in profile.breakdown if k not in ALWAYS]
    return [k for k in keys if k in NOTES[body]]
