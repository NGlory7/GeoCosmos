"""api/ testleri: CORS ayarı yayın adresleriyle doğru çalışıyor mu?"""
from api.main import DEFAULT_ORIGINS, parse_origins


def test_parse_origins_list_and_trailing_slash():
    raw = " http://localhost:5173 , https://geocosmos.vercel.app/ ,"
    assert parse_origins(raw) == ["http://localhost:5173", "https://geocosmos.vercel.app"]


def test_parse_origins_empty_falls_back_to_defaults():
    assert parse_origins(None) == list(DEFAULT_ORIGINS)
    assert parse_origins("  ") == list(DEFAULT_ORIGINS)
    assert "http://127.0.0.1:5173" in DEFAULT_ORIGINS
