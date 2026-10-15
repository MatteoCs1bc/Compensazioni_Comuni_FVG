import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.compensazioni import carica_regole, metodi_bess, proventi_bess, valore_scelto_bess
from core.fondo import fondo_perduto, fondo_rotativo
from core.fondo_docx import documento
from core.impresa_docx import atto_unilaterale, proposta, sollecito
from core.iter import carica_iter, regola_compensazione
from core.misure import AMMISSIBILITA, ID_STORICI, carica
from core.pavia import analisi, excel_analisi

R = carica_regole()
ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- database delle misure
def test_misure_integrita():
    d = carica()
    assert d.id.is_unique and len(d) >= 100
    assert set(d.ammissibilita) <= set(AMMISSIBILITA)
    amm = d[d.ammissibilita != "Esclusa"]
    assert (amm.costo_unitario_min <= amm.costo_unitario).all() and (amm.costo_unitario <= amm.costo_unitario_max).all()
    assert (amm.misura.str.len() > 0).all() and (d.nota_ammissibilita.str.len() > 0).all()
    assert ID_STORICI <= set(d.id), "i progetti salvati con la v0.2 devono ricaricarsi"


# ---------------------------------------------------------------- batterie sui proventi
def test_bess_proventi():
    prov = proventi_bess(137.75, 4, 13000)
    assert prov == pytest.approx(7_163_000)
    assert valore_scelto_bess(137.75, R, "bess_proventi") == pytest.approx(prov * 0.03 * 15)
    r = {x.metodo: x for x in metodi_bess(137.75, R)}["bess_proventi"]
    assert r.totale_min == pytest.approx(prov * 0.03 * 15) and r.totale_max == pytest.approx(prov * 0.04 * 15)


# ---------------------------------------------------------------- regole nel tempo
@pytest.mark.parametrize("data,regime,mw,tipo,corso,obbligo,pmin", [
    (date(2023, 9, 26), "au_regionale", 50, "fv", False, "no", 0),        # Cjase Sterpet: Linee guida 2010
    (date(2025, 1, 20), "au_regionale", 5, "fv", False, "sì", 0.01),      # TU FER, prima della L.R.
    (date(2025, 4, 10), "au_regionale", 4.356, "fv", False, "sì", 0.03),  # Risano: L.R. FVG
    (date(2025, 1, 14), "pas", None, "biometano", False, "dubbio", 0.01),
    (date(2025, 7, 1), "pas", 0.62, "fv", False, "no", 0),
    (None, "au_regionale", 190, "bess", True, "dubbio", 0.03),            # EAGLE 1
    (date(2026, 1, 1), "au_statale", 250, "bess", False, "dubbio", 0.01),
])
def test_regola(data, regime, mw, tipo, corso, obbligo, pmin):
    r = regola_compensazione(data, regime, mw, tipo, corso)
    assert r.obbligo == obbligo and r.perc_min == pmin


def test_iter_silenzio():
    it = carica_iter()
    conf = {f["id"]: f for f in it["fasi"]["au"]}
    assert conf["conferenza"]["silenzio"] == "assenso" and conf["convenzione"]["silenzio"] == "firma"
    assert {f.get("silenzio") for fasi in it["fasi"].values() for f in fasi} <= {None, "assenso", "firma", "non_blocca"}


# ---------------------------------------------------------------- Pavia
def test_pavia_analisi():
    fer = pd.read_csv(ROOT / "data" / "pavia" / "fer_pavia_al_2026-09-30.csv")
    a = analisi(fer, R)
    assert len(a) == len(fer)
    x = a.set_index("n")
    assert x.loc[4, "obbligo"] == "no" and x.loc[4, "rapporto"] < 0.01         # Cjase Sterpet sotto il 3%
    assert x.loc[8, "obbligo"] == "sì" and x.loc[8, "perc_min"] == 0.03        # Risano
    assert x.loc[19, "priorita"] == "Alta" and x.loc[2, "priorita"] == "Alta"  # EAGLE 1, Contessa
    assert x.loc[3, "obbligo"] == "no"                                          # sottostazione
    assert excel_analisi(a)[:2] == b"PK"


# ---------------------------------------------------------------- fondo per i cittadini
def test_fondo_perduto():
    e = fondo_perduto(0, 20000, 10, 400, 0.05)
    assert e[0].famiglie == 47 and e[-1].famiglie_cumulate >= 470


def test_fondo_rotativo_rientra():
    e = fondo_rotativo(100000, 0, 10, 5000, 5, insolvenza=0.0, costi_gestione=0.0)
    assert e[0].famiglie == 20
    assert e[-1].famiglie_cumulate > 20          # i rientri finanziano altre famiglie
    tot = e[-1].cassa_fine + e[-1].credito_in_essere
    assert tot == pytest.approx(100000, rel=1e-6)  # senza perdite il capitale si conserva


def test_documenti_word():
    p = {"comune": "Pavia Di Udine", "proponente": "X S.r.l.", "nome": "Test", "potenza_mw": 10,
         "compensazione_eur": 1_000_000, "compensazione_annua_eur": 33_000, "calcolo_testo": "calcolo"}
    inter = [{"nome": "Siepi", "quantita": "2000 metri", "costo": 50000}]
    for b in (documento("Pavia Di Udine", "rotativo", {"quota_annua": 20000}, [{"misura": "PdC", "unita": "contributo", "massimale": 1500}]),
              documento("", "perduto", {}, []), proposta(p, "PAS", inter), sollecito(p, "01/09/2026"),
              atto_unilaterale(p, "autorizzazione unica", inter)):
        assert b[:2] == b"PK" and len(b) > 5000
