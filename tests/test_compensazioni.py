"""I test riproducono i numeri della stima APE FVG per Pavia di Udine (24/02/2026)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.compensazioni import (ImpiantoProduzione, carica_regole, metodi_bess,
                                metodi_produzione, quota_ottenuta, valore_scelto_bess)

R = carica_regole()


def ape(potenza, produzione_mwh):
    return ImpiantoProduzione(potenza, produzione_mwh / potenza, 116.07, vita_utile_anni=30)


@pytest.mark.parametrize("p,prod,annuo,totale", [
    (6.37, 8518.62466, 29662.70, 889881.09),
    (4.98, 6659.7725, 23189.99, 695699.81),
    (7.04, 9414.61815, 32782.64, 983479.26),
])
def test_fotovoltaico_ape(p, prod, annuo, totale):
    r = {x.metodo: x for x in metodi_produzione(ape(p, prod), R)}["agenzia"]
    assert r.annuo == pytest.approx(annuo, abs=0.05)
    assert r.totale_min == pytest.approx(totale, abs=1)


def test_bess_ape():
    assert valore_scelto_bess(137.75, R, "bess_capex") == pytest.approx(2_892_750)
    assert valore_scelto_bess(90, R, "bess_capex", capex_eur_mw=800_000) == pytest.approx(2_160_000)
    assert valore_scelto_bess(137.75, R, "bess_annuo", eur_mw_anno=4000) == pytest.approx(9_642_500)
    assert valore_scelto_bess(90, R, "bess_annuo", eur_mw_anno=3500) == pytest.approx(5_512_500)
    assert valore_scelto_bess(137.75, R, "bess_una_tantum", eur_mw_una_tantum=40_000) == pytest.approx(5_510_000)
    assert valore_scelto_bess(90, R, "bess_una_tantum", eur_mw_una_tantum=30_000) == pytest.approx(2_700_000)


def test_bel_clima_esempio():
    imp = ImpiantoProduzione(60, 2000, 80, vita_utile_anni=1)
    r = {x.metodo: x for x in metodi_produzione(imp, R)}["bel_clima"]
    assert r.annuo == pytest.approx(384_000)


def test_sconto_riduce_valore():
    a = ImpiantoProduzione(10, 1337, 116.07, 30, 0.0)
    b = ImpiantoProduzione(10, 1337, 116.07, 30, 0.06)
    assert b.valore_vita_utile < a.valore_vita_utile
    assert b.fattore_anni() == pytest.approx(13.7648, abs=1e-3)


def test_atlas_quota():
    imp = ImpiantoProduzione(13.336, 1337, 116.07, 30)
    q = quota_ottenuta(180_000, imp)
    assert 0.0025 < q["su_proventi_vita_senza_sconto"] < 0.0035


def test_bess_range_ordinati():
    for r in metodi_bess(100, R):
        assert r.totale_min <= r.totale_max
