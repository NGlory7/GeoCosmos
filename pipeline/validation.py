"""Ünlü analog testi -> frontend/public/data/validation.json.

Her bilinen analog (config/known_analogs.yaml) kendi test amacında, ilgili hedeflere göre
Dünya karelerinin yüzde kaçlık diliminde?

- split=holdout: başarı ölçütü (en az min_hits tanesi en iyi top_percent içinde).
- split=tune:    sırası raporlanır; ağırlık ayarı sadece bunlara bakılarak yapılır.
- split=report:  sırası raporlanır, ölçüte girmez (ör. Lanzarote: lav tüpü verilerde görünmüyor).

Dönüş: {"hits": int, "min_hits": int, "top_percent": float, "analogs": [...]}
"""


def run_validation() -> dict:
    raise NotImplementedError("TODO")
