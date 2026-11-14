"""api/ testleri: CORS ayarı yayın adresleriyle doğru çalışıyor mu?"""
from api.main import DEFAULT_ORIGIN, parse_origins


def test_parse_origins_list_and_trailing_slash():
    raw = " http://localhost:5173 , https://geocosmos.vercel.app/ ,"
    assert parse_origins(raw) == ["http://localhost:5173", "https://geocosmos.vercel.app"]


def test_parse_origins_empty_falls_back_to_default():
    assert parse_origins(None) == [DEFAULT_ORIGIN]
    assert parse_origins("  ") == [DEFAULT_ORIGIN]
