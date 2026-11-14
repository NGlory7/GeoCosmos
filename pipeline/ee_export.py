"""Earth Engine -> data/raw/*.csv. Tüm karalar 25 km ızgara; SRTM, MODIS, ASTER, WorldCover.

Ham uydu verisi indirilmez; Earth Engine'de karelere küçültülür, sadece tablo iner."""


def export_grid(cell_km: int = 25) -> None:
    raise NotImplementedError("TODO")
