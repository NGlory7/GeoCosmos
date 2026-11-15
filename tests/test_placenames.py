"""Yer adları (pipeline/placenames.py): etiket, önbellek, analoglara yazma. Ağ isteği yapılmaz."""
import json

from core.schemas import Analog, Scores
from pipeline import placenames as pn
from pipeline.commentary import payload_for


def test_label_picks_local_state_country_without_duplicates():
    assert pn.label({"county": "Keriya County", "state": "Xinjiang", "country": "China"}) == \
        "Keriya County, Xinjiang, China"
    # yerel birim yoksa il + ülke; aynı ad iki kez yazılmaz
    assert pn.label({"state": "Nunavut", "region": "Nunavut", "country": "Canada"}) == "Nunavut, Canada"
    assert pn.label({}) is None


def test_turkish_label_falls_back_to_english_for_non_latin_parts():
    # Türkçe adı olmayan yerde Nominatim yerel yazıyı döndürür: o parça İngilizcesiyle değişir.
    tr = {"county": "于田县 كېرىيە ناھىيىسى", "state": "Sincan Uygur Özerk Bölgesi", "country": "Çin"}
    en = {"county": "Keriya County", "state": "Xinjiang", "country": "China"}
    assert pn.label(tr, fallback=en) == "Keriya County, Sincan Uygur Özerk Bölgesi, Çin"
    assert pn.is_latin("Şanlıurfa Çölü") and not pn.is_latin("于田县")


def test_mixed_script_names_are_cleaned():
    # OSM bazı adları iki yazıyla tutar; kartta sadece Latin harfli kısım kalır.
    assert pn.latin_only("Ad Dabbah  الدبة, Kuzey, Sudan") == "Ad Dabbah, Kuzey, Sudan"
    assert pn.latin_only("Halfa - حلفا, Northern State, Sudan") == "Halfa, Northern State, Sudan"
    assert pn.latin_only("أبو حمد, Nil Nehri, Sudan") == "Nil Nehri, Sudan"
    assert pn.latin_only("Keriya County, Sincan Uygur Özerk Bölgesi, Çin") == \
        "Keriya County, Sincan Uygur Özerk Bölgesi, Çin"
    assert pn.latin_only("الدبة") is None and pn.latin_only(None) is None


def _analog(cell_id: str, name: str = "36.29°K, 82.46°D") -> Analog:
    return Analog(id=cell_id, name=name, is_new=True, target_id="mars_gale", test_id="dust", lat=36.29,
                  lon=82.46, rank=1, score_total=80, scores=Scores(), params=[], breakdown=[])


def test_attach_places_reads_cache_only():
    cache = {"g25_a": {"lat": 1, "lon": 2, "tr": "Keriya, Sincan, Çin", "en": "Keriya, Xinjiang, China"},
             "g25_bos": {"lat": 1, "lon": 2, "tr": None, "en": None}}  # çözülemedi (ör. açık deniz)
    a, b, c = _analog("g25_a"), _analog("g25_bos"), _analog("g25_yok")
    pn.attach_places([a, b, c], cache)
    assert a.place and a.place.tr == "Keriya, Sincan, Çin" and a.place.en.endswith("China")
    assert b.place is None and c.place is None  # önbellekte yoksa koordinatla kalır, ağ isteği yok
    assert a.name == "36.29°K, 82.46°D"  # name değişmez


def test_place_does_not_change_gemini_prompt():
    # Yorum önbelleği istem özetine bağlı: place eklenince 125 yorum geçersiz olmamalı.
    a = _analog("g25_a")
    before = payload_for(a.model_dump(), {})
    pn.attach_places([a], {"g25_a": {"tr": "Keriya, Sincan, Çin", "en": "Keriya, Xinjiang, China"}})
    assert a.place is not None
    assert payload_for(a.model_dump(), {}) == before


def test_write_places_updates_only_place(tmp_path):
    feat = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [82.46, 36.29]},
            "properties": {**_analog("g25_a").model_dump(), "ai_comment": "yorum"}}
    path = tmp_path / "mars_gale_dust.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [feat]}), encoding="utf-8")
    n = pn.write_places(tmp_path, {"g25_a": {"tr": "Keriya, Sincan, Çin", "en": "Keriya, Xinjiang, China"}})
    props = json.loads(path.read_text(encoding="utf-8"))["features"][0]["properties"]
    assert n == 1 and props["place"]["en"] == "Keriya, Xinjiang, China" and props["ai_comment"] == "yorum"
