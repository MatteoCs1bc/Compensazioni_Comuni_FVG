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


# ---------------------------------------------------------------- scheda compensazioni Pavia
def test_pavia_scheda():
    from core.pavia import carica_scheda, scheda_docx, totali_scheda
    s = carica_scheda()
    t = totali_scheda(s)
    assert t["una_tantum_noto"] == pytest.approx(1_400_000 + 1_000_000 + 850_000 + 144_967.68)
    assert t["bess_eur_mw_min"] == pytest.approx(7000) and t["bess_eur_mw_max"] == pytest.approx(1_000_000 / 90)
    assert set(s["priorita_df"].priorita) <= {"Alta", "Media", "Bassa"}
    assert scheda_docx(s)[:2] == b"PK"


# ---------------------------------------------------------------- registro VIA FVG
def test_registro_via():
    v = pd.read_csv(ROOT / "data" / "territorio" / "registro_via_fvg.csv").fillna("")
    assert v.id.is_unique and len(v) >= 20
    assert set(v.categoria) <= {"Rinnovabili", "Fossili", "Reti", "Trasporti"}
    assert v.comuni.str.contains("Pavia di Udine").sum() >= 3


def test_mappa_pavia():
    from core.pavia import figura_mappa, impianti_mappa
    df = impianti_mappa()
    assert df.id.is_unique and len(df) >= 25
    # tutti gli impianti dell'elenco comunale (tranne la 5, che è dentro la 4 come compensazione, è comunque mappata)
    import pandas as pd
    fer = pd.read_csv("data/pavia/fer_pavia_al_2026-10-20.csv", dtype={"n": str})
    # tutti gli impianti della tabella del Comune al 20/10 sono sulla mappa, più il biogas (n. 10) dell'elenco al 30/09
    assert set(fer.n) | {"10"} == set(df.n) - {""}
    # stati come nella tabella del Comune: Santo Stefano realizzato, KI Italia respinte
    st = df.drop_duplicates("n").set_index("n").stato
    assert st["3"] == "Realizzato" and st["17"] == st["18"] == "Respinta" and st["19"] == "In corso"
    # la scheda «0, 01» non deve sovrascrivere l'impianto n. 1 (BESS Enel)
    assert "1.400.000" in df[df.n == "1"].compensazione.iloc[0]
    # dentro il comune: bounding box del confine
    for r in df.itertuples():
        assert 13.23 < r.lon_c < 13.35 and 45.948 < r.lat_c < 46.013, r.id
    # georeferenziazione: BESS Enel (n. 1) entro ~100 m dalle coordinate del portale regionale
    b = df[df.id == "1"].iloc[0]
    assert abs(b.lon_c - 13.28851) < 0.0013 and abs(b.lat_c - 45.96269) < 0.0009
    # superfici coerenti con l'elenco comunale (Contessa e Cjase Sterpet entro il 10%)
    for n, ha in (("2", 45.75), ("4", 38.68)):
        assert abs(df[df.n == n].ha_mappa.sum() - ha) / ha < 0.1
    fig = figura_mappa(df, ["Realizzato", "In corso", "Respinta"], "white-bg")
    assert len(fig.data) >= 4


def test_osm_pavia():
    from core.pavia import figura_mappa, impianti_mappa, osm_pavia
    osm = osm_pavia()
    linee = [f for f in osm["features"] if f["properties"]["tipo"] == "linea"]
    assert {380, 220, 132} <= {f["properties"]["tensione_kv"] for f in linee}
    # il fotovoltaico OSM di San Mauro coincide con l'impianto 0a del Comune ed è stato scartato
    assert "way/768604088" not in {f["properties"]["osm_id"] for f in osm["features"]}
    fig = figura_mappa(impianti_mappa(), None, "white-bg", osm=osm)
    nomi = {t.name for t in fig.data}
    assert "Linea 380 kV" in nomi and any("fuori elenco" in (n or "") for n in nomi)
    # legenda leggibile col tema scuro: testo scuro esplicito, rete OSM nella seconda legenda
    assert fig.layout.legend.font.color == "#1f2933" and fig.layout.legend2.title.text
    assert all(t.legend == "legend2" for t in fig.data if (t.name or "").startswith("Linea"))


def test_mappa_fvg():
    from core.mappe import STATI_FVG, figura_fvg, osm_fvg, progetti_fvg
    df = progetti_fvg()
    assert len(df) > 200 and df.stato.isin(STATI_FVG).all()
    assert df.lon.between(12.3, 13.95).all() and df.lat.between(45.55, 46.7).all()
    # accumuli dal registro corretto: Aukera 137,75 MW, non 1.377,5
    assert df[(df.categoria == "Accumuli")].potenza_mw.max() < 1000
    osm = osm_fvg()
    kv = {f["properties"].get("tensione_kv") for f in osm["features"] if f["properties"]["tipo"] == "linea"}
    assert kv == {132, 220, 380}
    fig = figura_fvg(df, osm, ["Solare", "Accumuli"], STATI_FVG)
    nomi = {t.name for t in fig.data}
    assert {"Solare", "Accumuli", "Linea 380 kV", "Fotovoltaico a terra esistente",
            "Stazioni AT (Terna)", "Cabine primarie AT/MT"} <= nomi
    tutti = figura_fvg(df, osm, ["Solare"], STATI_FVG, {"aree", "secondarie"})
    assert {"Aree di cabina primaria", "Cabine secondarie MT/BT"} <= {t.name for t in tutti.data}


def test_cabine_osm():
    from core.mappe import cabine_fvg, dati_aree
    c = [f["properties"] for f in cabine_fvg()["features"]]
    n = {k: sum(p["classe"] == k for p in c) for k in ("stazione", "primaria", "secondaria", "centrale")}
    assert n["stazione"] >= 4 and n["primaria"] >= 50 and n["secondaria"] > 5000 and n["centrale"] > 100
    assert any(p.get("nome") == "SE Udine Sud" and p["classe"] == "stazione" for p in c)
    # ogni cabina primaria cade in un'area di cabina primaria nota
    a = dati_aree()
    assert all(p.get("area") in set(a.codice) for p in c if p["classe"] == "primaria")
    assert a.sezioni_invertite.sum() > 0


def test_au_fv_verificate_sul_bur():
    import pandas as pd
    au = pd.read_csv("data/territorio/au_fv_2025_2026.csv")
    assert len(au) == 23 and au["ID progetto"].is_unique
    assert (au["Stato verifica"] == "Verificato sul BUR").all()
    assert au["Numero decreto"].notna().all() and au["Proponente"].notna().all()
    crimea = au[au["ID progetto"] == "FVG-2026-006"].iloc[0]
    assert crimea["Numero decreto"] == "17640/GRFVG" and "Manzano" in crimea["Comune/i sede impianto"]
    rel = pd.read_csv("data/territorio/au_fv_2025_2026_comuni.csv")
    pav = rel[rel.Comune == "Pavia di Udine"]
    assert set(pav[pav["Ruolo territoriale"] == "Comune sede impianto"]["ID progetto"]) == {"FVG-2025-003", "FVG-2025-016", "FVG-2026-006"}
    assert "FVG-2025-006" in set(pav["ID progetto"])          # Trivignano Solar 1: solo connessione
    c = pd.read_csv("data/territorio/comuni_indicatori.csv").set_index("comune")
    assert c.loc["Pavia Di Udine", "au_fv_n"] == 3 and c.loc["Talmassons", "au_fv_n"] == 1


def test_suolo_pavia():
    from core.suolo import (carica_suolo, conti, consumo_fvg, figura_affiancati, figura_annidati, figura_pannelli,
                            gruppi_tetto, serie_consumo, voci_panoramica)
    df = consumo_fvg()
    assert len(df) == 216  # 215 comuni FVG + la riga regionale
    r = df[df.comune == "Pavia di Udine"].iloc[0]
    assert r.consumato_2025_ha == 557.02 and abs(r.consumato_2025_pct - 16.298) < 1e-6
    assert abs(r.tetti_fv_min_ha - 29.247) < 0.01 and abs(r.tetti_fv_max_ha - 38.2) < 0.01
    c = conti(carica_suolo(), r)
    assert abs(c["tetto"] - 57.945) < 0.01           # 3% di 1.931,5 ha
    assert abs(c["fv_aut"] - 56.09) < 0.01           # FV autorizzato in zona agricola
    assert abs(c["bess_aut"] + c["bess_in_corso"] - 24.02) < 0.01  # Lauzacco (H2) escluso
    assert abs(c["netto_2021_2025"] - 25.29) < 0.01
    assert abs(serie_consumo(r).ha.sum() - 64.04) < 0.01
    for f in (figura_affiancati(voci_panoramica(c)), figura_annidati(voci_panoramica(c, True)),
              figura_pannelli(gruppi_tetto(c))):
        assert f.layout.meta["larghezza_px"] <= 840   # entra nella colonna centrale senza rimpicciolirsi


def test_suolo_confronti():
    from core.suolo import (carica_suolo, conti, consumo_fvg, figura_rispetto_sau, figura_territorio,
                            ripartizione_territorio, rispetto_sau)
    s = carica_suolo()
    c = conti(s, consumo_fvg().query("comune == 'Pavia di Udine'").iloc[0])
    assert abs(c["realizzati"] - 59.72) < 0.01
    rip = ripartizione_territorio(c, s)
    figli = rip[rip.padre == "Territorio comunale"].ha.sum()
    assert abs(figli - c["superficie"]) < 0.01          # SAU + consumato + resto = territorio
    assert abs(rip[rip.padre == "Superficie agricola (SAU)"].ha.sum() - c["sau"]) < 0.01
    r = rispetto_sau(c, s).set_index("voce")
    assert abs(r.loc["Fotovoltaico a terra autorizzato · reversibile", "pct_sau"] - 2.904) < 0.01
    assert abs(r.loc["Suolo consumato in totale (reversibile + permanente)", "pct_sau"] - 28.84) < 0.01
    # impianti realizzati separati tra consumo reversibile (fotovoltaico) e permanente (accumuli, stazione, biometano)
    assert abs(c["realizzati_rev"] - 45.61) < 0.01 and abs(c["realizzati_perm"] - 14.11) < 0.01
    assert c["mais_pavia"] == 6                                     # dato del Comune
    con = ripartizione_territorio(c, s).set_index("voce")
    assert abs(con.loc["Colture per il biometano", "ha"] - 6) < 1e-9
    senza = ripartizione_territorio(c, s, mais=False)
    assert abs(senza[senza.padre == "Superficie agricola (SAU)"].ha.sum() - c["sau"]) < 0.01
    figura_territorio(rip); figura_rispetto_sau(rispetto_sau(c, s))


def test_mais_biometano():
    from core.suolo import carica_suolo, ettari_mais, quota_metano_colture, quota_nuova, smc_prima
    m = carica_suolo()["mais_biometano"]
    assert abs(ettari_mais(m) - 554.5) < 1           # 30.500 t / 55 t/ha
    assert abs(ettari_mais(m, 45) - 677.8) < 1
    assert 0.8 < quota_metano_colture(m) <= 1.0      # le colture coprono gran parte del metano previsto
    assert abs(smc_prima(m) - 2.114e6) < 5e3         # biogas 999 kWe del 2012
    assert 0.45 < quota_nuova(m) < 0.55


def test_tetto_unico():
    from core.suolo import carica_suolo, conti, consumo_fvg, figura_pannelli, gruppo_tetto_unico
    s = carica_suolo()
    c = conti(s, consumo_fvg().query("comune == 'Pavia di Udine'").iloc[0])
    assert abs(c["unico_aut"] - (56.09 + 13.36 + 4.70)) < 0.01   # FV + accumuli + biometano autorizzati
    assert c["unico_aut"] > c["tetto"]                             # con il tetto unico è già superato
    assert abs(c["unico_in_corso"] - (45.75 + 10.66)) < 0.01       # Contessa + EAGLE 1
    assert "accumulo elettrochimico" in s["tetto"]["testo_vigente"]  # testo citato alla lettera
    assert len(s["tetto"]["letture"]) == 2
    figura_pannelli(gruppo_tetto_unico(c))
