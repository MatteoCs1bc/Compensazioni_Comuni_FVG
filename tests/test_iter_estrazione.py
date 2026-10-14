import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.convenzione_docx import bozza
from core.estrazione import analizza, potenze
from core.iter import carica_iter, determina_regime


@pytest.mark.parametrize("tipo,mw,area,atteso", [
    ("fv_terra", 0.8, "ordinaria", "pas"),
    ("fv_terra", 5.7, "ordinaria", "au_regionale"),
    ("fv_terra", 5.7, "idonea", "pas"),
    ("fv_terra", 13.3, "idonea", "au_regionale"),
    ("fv_terra", 4.0, "industriale", "libera"),
    ("fv_terra", 12.0, "industriale", "pas"),
    ("agrivoltaico", 4.0, "ordinaria", "libera"),
    ("agrivoltaico", 13.336, "ordinaria", "au_regionale"),
    ("eolico", 60, "ordinaria", "au_regionale"),
    ("eolico", 0.05, "ordinaria", "pas"),
    ("bess", 8, "ordinaria", "libera"),
    ("bess", 137.75, "ordinaria", "au_regionale"),
    ("bess", 250, "ordinaria", "au_statale"),
    ("fv_edificio", 0.5, "ordinaria", "libera"),
])
def test_regime(tipo, mw, area, atteso):
    assert determina_regime(tipo, mw, area).regime == atteso


def test_compensazioni_per_regime():
    assert determina_regime("fv_terra", 5.7, "idonea").perc_max == 0.03       # PAS > 1 MW
    e = determina_regime("fv_terra", 13.3, "ordinaria")
    assert (e.perc_min, e.perc_max) == (0.03, 0.04)                            # AU FVG > 1 MW
    assert determina_regime("fv_terra", 0.8, "ordinaria").perc_max == 0.0     # PAS sotto 1 MW


def test_fasi_hanno_campi():
    it = carica_iter()
    for chiave in ("au", "pas", "libera"):
        for f in it["fasi"][chiave]:
            assert f["titolo"] and f["cosa"] and isinstance(f["comune"], list)


def test_estrazione_potenza():
    t = ("I lavori riguardano un lotto di impianti fotovoltaici a terra della potenza complessiva di 5.696,34 kW. "
         "Ciascun modulo ha potenza di 670 Wp. La potenza nominale del gruppo di conversione cc/ca sarà pari a 2.856,88 kW.")
    a = analizza(t, ["San Giovanni Al Natisone"])
    assert a["potenza_mw"] == pytest.approx(5.69634, abs=1e-3)
    assert any(v == pytest.approx(13.336) for v, _ in potenze("impianto di potenza nominale complessiva 13,336 MW"))


def test_bozza_docx():
    b = bozza({"comune": "Pavia Di Udine", "proponente": "X S.r.l.", "nome": "Test", "potenza_mw": 10,
               "compensazione_eur": 1_000_000, "percentuale": 3.0},
              {"annuale": True, "garanzia": True, "subentro": True, "rendiconto": True, "penali": True, "realizza": "Comune"},
              [{"nome": "Siepi", "quantita": "2000 metri", "costo": 50000}])
    assert b[:2] == b"PK" and len(b) > 5000
