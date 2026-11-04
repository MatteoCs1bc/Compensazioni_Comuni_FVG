"""Analisi per singolo progetto del Comune di Pavia di Udine."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from core.compensazioni import ImpiantoProduzione, _it, carica_regole, proventi_bess
from core.iter import NOMI_REGIME, regola_compensazione

ROOT = Path(__file__).resolve().parents[1]
CARTELLA = ROOT / "data" / "pavia"

NOMI_REGIME_EXTRA = dict(NOMI_REGIME, rete="Opera di rete", compensazione="Compensazione di un altro impianto",
                         libera="Attività libera / edilizia libera")
PRIORITA = {"Alta": 0, "Media": 1, "Bassa": 2, "—": 3}


def carica_analisi() -> dict:
    with open(CARTELLA / "analisi_progetti.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _data(x):
    if x is None or isinstance(x, date):
        return x
    return date.fromisoformat(str(x))


def valori(tipo: str, mw: float | None, regole: dict) -> tuple[float | None, float | None, str]:
    """(base su cui si applica la percentuale, riferimento al 3%, descrizione della base)."""
    if not mw or tipo in ("rete", "biometano"):
        return None, None, ""
    d = regole["default_fvg"]
    if tipo == "bess":
        b = d["bess"]
        prov = proventi_bess(mw, b["durata_ore"], b["premio_capacita_eur_mwh_anno"], b["altri_ricavi_eur_mw_anno"])
        base = prov * b["anni_proventi"]
        return base, base * 0.03, (f"proventi stimati {_it(prov)} €/anno × {b['anni_proventi']} anni "
                                   f"(ipotesi: {b['durata_ore']} ore, premio di capacità {_it(b['premio_capacita_eur_mwh_anno'])} €/MWh)")
    imp = ImpiantoProduzione(mw, d["ore_equivalenti"]["fotovoltaico"], d["prezzo_eur_mwh"], d["vita_utile_anni"])
    base = imp.proventi_anno * imp.vita_utile_anni
    return base, base * 0.03, f"proventi stimati {_it(imp.proventi_anno)} €/anno × {imp.vita_utile_anni} anni"


def margine(stato: str, regime: str, obbligo: str, in_corso: bool, archiviato: bool) -> tuple[str, str]:
    if archiviato:
        return "Archiviato: nessuna azione, ma prepararsi a una ripresentazione", "Bassa"
    if regime in ("rete", "compensazione"):
        return "—", "—"
    if in_corso:
        return "In istruttoria: si negozia l'importo in conferenza", "Alta"
    if stato == "Autorizzato":
        if obbligo in ("sì", "dubbio"):
            return "Autorizzato, non realizzato: convenzione e modalità di spesa ancora aperte", "Alta"
        return "Non realizzato: possibile accordo volontario", "Media"
    if obbligo in ("sì", "dubbio"):
        return "Realizzato: verificare che quanto dovuto sia stato dato", "Media"
    return "Chiuso: verificare eventuali impegni scritti nel titolo", "Bassa"


def analisi(fer: pd.DataFrame, regole: dict | None = None) -> pd.DataFrame:
    regole = regole or carica_regole()
    a = carica_analisi()
    info = {p["n"]: p for p in a["progetti"]}
    righe = []
    for _, r in fer.iterrows():
        x = info.get(int(r["n"]), {})
        regime = x.get("regime", "au_regionale")
        tipo = x.get("tipo", "fv")
        mw = None if pd.isna(r["potenza_mw"]) else float(r["potenza_mw"])
        archiviato = bool(x.get("archiviato")) or r["stato"] == "Archiviata"
        in_corso = bool(x.get("in_corso"))
        if regime == "compensazione":
            reg = None
        elif archiviato:
            reg = regola_compensazione(date.today(), x.get("regime_se_ripresentato", regime), mw, tipo, True)
            reg.periodo = "se ripresentato oggi"
        else:
            reg = regola_compensazione(_data(x.get("data_titolo")), regime, mw, tipo, in_corso)
        base, rif3, base_txt = valori(tipo, mw, regole) if regime not in ("rete", "compensazione") else (None, None, "")
        presc = x.get("compensazione_prescritta_eur")
        marg, prio = margine(r["stato"], regime, reg.obbligo if reg else "no", in_corso, archiviato)
        righe.append({
            "n": int(r["n"]), "impianto": r["denominazione"], "tipo": r["tipo"], "mw": mw, "stato": r["stato"],
            "anno": r["anno"], "localita": r["localizzazione"], "zona": x.get("zona", ""),
            "ente": r["ente"], "provvedimento": r["provvedimento"],
            "sup_complessiva_ha": r["sup_complessiva_ha"], "sup_recintata_ha": r["sup_recintata_ha"],
            "sup_agricola_ha": r["sup_agricola_mitigazione_ha"],
            "regime": NOMI_REGIME_EXTRA.get(regime, regime), "data_titolo": _data(x.get("data_titolo")),
            "data_nota": x.get("data_nota", ""),
            "regola_periodo": reg.periodo if reg else "—", "obbligo": reg.obbligo if reg else "—",
            "perc_min": reg.perc_min if reg else None, "perc_max": reg.perc_max if reg else None,
            "regola_testo": reg.testo if reg else "Vedi l'impianto collegato.",
            "base_eur": base, "base_testo": base_txt, "riferimento_3pct": rif3,
            "minimo_legge": base * reg.perc_min if (base and reg) else None,
            "massimo_legge": base * reg.perc_max if (base and reg) else None,
            "prescritta": x.get("compensazione_prescritta", ""), "prescritta_eur": presc,
            "prescritta_stima": bool(x.get("compensazione_prescritta_stima")),
            "rapporto": (presc / base) if (presc and base) else None,
            "margine": marg, "priorita": prio, "proponente": x.get("proponente", ""), "portale": x.get("portale", ""),
            "bur": x.get("bur", ""), "note": x.get("note", []), "collegato_a": x.get("collegato_a"),
            "archiviato": archiviato, "in_corso": in_corso,
        })
    df = pd.DataFrame(righe)
    df["_o"] = df.priorita.map(PRIORITA)
    return df.sort_values(["_o", "n"]).drop(columns="_o").reset_index(drop=True)


def gruppi_zona(df: pd.DataFrame) -> pd.DataFrame:
    """Cumulo per zona: progetti attivi, MW, ettari agricoli."""
    att = df[~df.archiviato & (df.regime != NOMI_REGIME_EXTRA["compensazione"])]
    g = att.groupby("zona").agg(progetti=("n", "count"), mw=("mw", "sum"), ha_agricoli=("sup_agricola_ha", "sum"))
    return g.sort_values("mw", ascending=False).reset_index()


def excel_analisi(df: pd.DataFrame) -> bytes:
    import io
    cols = {"n": "N.", "impianto": "Impianto", "tipo": "Tipo", "mw": "MW", "stato": "Stato", "zona": "Zona",
            "regime": "Procedura", "provvedimento": "Titolo", "regola_periodo": "Regole applicabili",
            "obbligo": "Obbligo di compensare", "regola_testo": "Regola", "base_testo": "Base di calcolo",
            "riferimento_3pct": "Riferimento al 3% (€)", "minimo_legge": "Minimo per le regole del periodo (€)",
            "massimo_legge": "Massimo per le regole del periodo (€)", "prescritta": "Compensazione prescritta",
            "prescritta_eur": "Valore prescritto (€)", "priorita": "Priorità", "margine": "Cosa può fare il Comune",
            "proponente": "Proponente", "portale": "Portale regionale"}
    out = df[list(cols)].rename(columns=cols).copy()
    out["Note"] = df["note"].apply(lambda n: " | ".join(n))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="Analisi", index=False)
        ws = xw.sheets["Analisi"]
        for col, w in {"B": 34, "G": 30, "H": 34, "I": 26, "K": 70, "L": 50, "P": 40, "S": 50, "V": 90}.items():
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "C2"
    return buf.getvalue()


# ------------------------------------------------------------------ scheda compensazioni (documenti del Comune)
def carica_scheda() -> dict:
    """Scheda compensazioni costruita sui decreti e sulle schede FER forniti dal Comune."""
    with open(CARTELLA / "scheda_compensazioni.yaml", encoding="utf-8") as f:
        s = yaml.safe_load(f)
    imp = pd.DataFrame(s["impianti"])
    imp["eur_mw"] = imp.apply(lambda r: r.eur / r.mw if pd.notna(r.eur) and r.mw else None, axis=1)
    s["impianti_df"] = imp
    s["priorita_df"] = pd.DataFrame(s["priorita"])
    s["confronto_df"] = pd.DataFrame(s["confronto"]["righe"])
    return s


def totali_scheda(s: dict) -> dict:
    imp = s["impianti_df"]
    bess = imp[(imp.tipo == "BESS") & imp.eur_mw.notna()]
    return {"una_tantum_noto": float(imp.eur.sum(skipna=True)),
            "bess_eur_mw_min": float(bess.eur_mw.min()), "bess_eur_mw_max": float(bess.eur_mw.max()),
            "annuali": int((imp.modalita == "annuale").sum()),
            "aperti": int((s["priorita_df"].priorita == "Alta").sum())}


def _mw(x) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")


def scheda_docx(s: dict) -> bytes:
    """La scheda in Word, orizzontale, pronta da stampare."""
    import io

    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Cm, Pt

    d = Document()
    sez = d.sections[0]
    sez.orientation = WD_ORIENT.LANDSCAPE
    sez.page_width, sez.page_height = sez.page_height, sez.page_width
    for lato in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sez, lato, Cm(1.5))
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(10)

    def tabella(intest, righe, larghezze=None):
        t = d.add_table(rows=1, cols=len(intest))
        t.style = "Light Grid Accent 1"
        for c, x in zip(t.rows[0].cells, intest):
            c.text = x
        for r in righe:
            for c, x in zip(t.add_row().cells, r):
                c.text = "" if x is None else str(x)
        if larghezze:
            for riga in t.rows:
                for c, w in zip(riga.cells, larghezze):
                    c.width = Cm(w)

    d.add_heading(s["titolo"], level=1)
    agg = s["aggiornato_al"]
    d.add_paragraph(f"Aggiornata al {agg.strftime('%d/%m/%Y') if hasattr(agg, 'strftime') else agg}").runs[0].italic = True
    d.add_paragraph(s["sintesi"].strip())

    d.add_heading("Cosa emerge dai documenti", level=2)
    for x in s["novita"]:
        p = d.add_paragraph(style="List Bullet")
        p.add_run(x["titolo"] + ". ").bold = True
        p.add_run(x["testo"].strip())

    d.add_heading("Compensazioni impianto per impianto", level=2)
    imp = s["impianti_df"]
    tabella(["N.", "Impianto", "MW", "Titolo", "Compensazione per Pavia", "€/MW", "Stato"],
            [(r.n, r.impianto, _mw(r.mw), r.titolo, r.compensazione,
              _it(r.eur_mw) if pd.notna(r.eur_mw) else ("annuale" if r.modalita == "annuale" else "–"), r.stato)
             for r in imp.itertuples()], [1.2, 5, 1.5, 4, 8, 1.8, 3.5])
    for n in s.get("note_impianti", []):
        d.add_paragraph(n).runs[0].italic = True

    d.add_heading("Pavia e Santa Maria la Longa a confronto", level=2)
    d.add_paragraph(s["confronto"]["testo"].strip())
    tabella(["Impianto", "Pavia di Udine", "Santa Maria la Longa"],
            [(r.impianto, r.pavia, r.smll) for r in s["confronto_df"].itertuples()], [6, 8, 11])

    d.add_heading("Progetti da seguire adesso", level=2)
    tabella(["Priorità", "N.", "Impianto", "Situazione", "Cosa fare"],
            [(r.priorita, r.n, r.impianto, r.situazione, r.azione) for r in s["priorita_df"].itertuples()],
            [1.8, 1.2, 5.5, 8, 8])

    d.add_heading("Cosa pretendere nelle prossime convenzioni", level=2)
    for x in s["clausole"]:
        d.add_paragraph("☐ " + x)
    d.add_heading("Documenti ancora da recuperare", level=2)
    for x in s["documenti"]:
        d.add_paragraph("☐ " + x)
    p = d.add_paragraph("Fonti: " + s["fonti"].strip())
    p.runs[0].italic = True
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Mappa interattiva degli impianti
# ---------------------------------------------------------------------------
COLORI_STATO = {"Realizzato": "#2e7d32", "Autorizzato": "#f2c200", "In corso": "#f57c00",
                "Respinta": "#9e9e9e", "Rete Terna": "#c62828"}
SIMBOLO_TIPO = {"FV": "Fotovoltaico", "BESS": "Accumulo (BESS)", "BIOMETANO": "Biogas / biometano", "RETE": "Rete elettrica"}


def _rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def _a_capo(testo, larghezza: int = 60) -> str:
    import textwrap
    if not isinstance(testo, str) or not testo:
        return ""
    return "<br>".join(textwrap.wrap(testo, larghezza))


ELENCO_MAPPA = "fer_pavia_al_2026-10-20.csv"   # tabella del Comune aggiornata al 20/10/2026
NUMERO_DA_POLIGONO = {"0a": "00", "0b": "01"}   # la mappa Insiel indica «0» per entrambi gli impianti del 2012
STATO_MAPPA = {"Iter in corso": "In corso", "Archiviata": "Respinta"}


def _chiavi_scheda(n) -> list[str]:
    """«0, 01» -> ["00", "01"]; «17, 18» -> ["17", "18"]."""
    out = []
    for k in str(n).replace(" ", "").split(","):
        out.append({"0": "00", "00": "00", "01": "01"}.get(k, k))
    return out


def impianti_mappa() -> pd.DataFrame:
    """Un poligono (o punto) per riga, con i dati dell'elenco comunale e della scheda compensazioni.

    Fonte dei dati: tabella del Comune al 20/10/2026. Il biogas (n. 10) c'è solo nell'elenco al 30/09/2026."""
    import json
    with open(CARTELLA / "impianti_pavia.geojson", encoding="utf-8") as f:
        gj = json.load(f)
    fer = pd.read_csv(CARTELLA / ELENCO_MAPPA, dtype={"n": str})
    vecchio = pd.read_csv(CARTELLA / "fer_pavia_al_2026-09-30.csv", dtype={"n": str})
    solo_vecchio = vecchio[~vecchio.n.isin(fer.n) & (vecchio.n != "0")].assign(
        note="Presente nell'elenco comunale al 30/09/2026 ma non nella tabella del 20/10/2026: da chiarire con l'ufficio tecnico")
    fer = pd.concat([fer, solo_vecchio], ignore_index=True).set_index("n")
    dubbio = ("Posizione da confermare: la mappa del Comune indica «0» per entrambi gli impianti del 2012; "
              "qui sono attribuiti per vicinanza a via San Mauro e alla frazione di Selvuzzis. ")
    fer.loc["00", "note"] = dubbio + "198 kW sono pochi per un poligono di circa 3 ettari: potrebbero essere invertiti. " + fer.loc["00", "note"]
    fer.loc["01", "note"] = dubbio
    s = carica_scheda()
    imp, pri = {}, {}
    for r in s["impianti"]:
        for k in _chiavi_scheda(r["n"]):
            imp[k] = r
    for r in s["priorita"]:
        for k in _chiavi_scheda(r["n"]):
            pri[k] = r
    righe = []
    for ft in gj["features"]:
        p = ft["properties"]
        rif = p["rif"]
        terna = rif.startswith("terna")
        n = NUMERO_DA_POLIGONO.get(rif, rif)
        f = None if terna or n not in fer.index else fer.loc[n]
        if terna:
            stato, tipo = "Rete Terna", "RETE"
        else:
            stato, tipo = STATO_MAPPA.get(f.stato, f.stato), ("FV" if f.tipo == "AgriFV" else f.tipo)
        sc, pr = imp.get(n), pri.get(n)
        nome = p["nome"] if terna else (sc["impianto"] if sc and n not in ("00", "01") else f.denominazione)
        if f is not None and str(f.denominazione).startswith("Compensazione") and "4" in imp:
            comp = f"È la compensazione per il Comune dell'impianto Cjase Sterpet (n. 4): {imp['4']['stato']}"
        elif sc:
            comp = f"{sc['compensazione']} ({sc['stato']})"
        elif pr:
            comp = f"{pr['situazione']} → {pr['azione']}"
        elif terna:
            comp = "Opera di rete Terna: compensazioni ai Comuni ai sensi della L. 239/2004, art. 1, c. 5"
        else:
            comp = "Nessuna informazione nella scheda"
        g = ft["geometry"]
        if g["type"] == "Polygon":
            ring = g["coordinates"][0]
            lon, lat = [c[0] for c in ring], [c[1] for c in ring]
        else:
            lon, lat = [g["coordinates"][0]], [g["coordinates"][1]]
        val = lambda col: (f[col] if f is not None and col in f and pd.notna(f[col]) else None)
        righe.append({
            "id": p["id"], "n": "" if terna else n, "nome": nome, "tipo": tipo,
            "tipo_esteso": ("Agrivoltaico" if f is not None and f.tipo == "AgriFV" else SIMBOLO_TIPO.get(tipo, tipo)),
            "stato": stato, "societa": val("societa") or "", "localizzazione": val("localizzazione") or "",
            "mw": val("potenza_mw"), "ha_comune": val("sup_complessiva_ha"),
            "ha_mappa": p["ha_mappa"], "titolo": val("provvedimento") or "", "ente": val("ente") or "",
            "nota": val("note") or "", "compensazione": comp, "geometria": g["type"],
            "lon": lon, "lat": lat, "lon_c": p["centro"][0], "lat_c": p["centro"][1],
        })
    return pd.DataFrame(righe)


def osm_pavia() -> dict:
    """Linee elettriche e altri impianti fotovoltaici da OpenStreetMap, ritagliati sull'area di Pavia."""
    import json
    with open(CARTELLA / "osm_pavia.geojson", encoding="utf-8") as f:
        return json.load(f)


RIQUADRO_PAVIA = (13.20, 13.38, 45.935, 46.025)


def _tracce_osm(fig, osm: dict, centri: list | None = None):
    """Linee AT, cabine (stazioni, primarie, secondarie) e centrali OSM nel riquadro di Pavia.
    Le centrali a meno di 150 m da un impianto dell'elenco comunale sono doppioni e vengono saltate."""
    import math
    import plotly.graph_objects as go
    from core.mappe import cabine_fvg, tracce_cabine, tracce_centrali, tracce_linee
    tracce_linee(fig, osm["features"])
    x0, x1, y0, y1 = RIQUADRO_PAVIA

    def vicino(xy):
        return any(math.hypot((xy[0] - c[0]) * 77400, (xy[1] - c[1]) * 110540) < 150 for c in centri or [])

    cab = [f for f in cabine_fvg()["features"]
           if x0 < f["geometry"]["coordinates"][0] < x1 and y0 < f["geometry"]["coordinates"][1] < y1
           and not (f["properties"]["classe"] == "centrale" and vicino(f["geometry"]["coordinates"]))]
    tracce_cabine(fig, cab)
    tracce_centrali(fig, cab)
    fv = [f for f in osm["features"] if f["properties"]["tipo"] == "fv"]
    if fv:
        lon, lat = [], []
        for f in fv:
            for x, y in f["geometry"]["coordinates"][0]:
                lon.append(x); lat.append(y)
            lon.append(None); lat.append(None)
        nome = "Altri fotovoltaici (fuori elenco comunale)"
        fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", fill="toself", fillcolor="rgba(84,110,122,0.35)",
                                    line=dict(color="#546e7a", width=1.5), name=nome, legendgroup="fv_osm",
                                    hoverinfo="skip", legend="legend2"))
        fig.add_trace(go.Scattermap(
            lon=[f["properties"]["centro"][0] for f in fv], lat=[f["properties"]["centro"][1] for f in fv],
            mode="markers", marker=dict(size=8, color="#546e7a"), legendgroup="fv_osm", showlegend=False, legend="legend2",
            hovertext=[f"<b>{f['properties'].get('nome') or 'Fotovoltaico a terra'}</b><br>"
                       f"Circa {_mw(f['properties']['ha'])} ha (superficie del poligono OSM)"
                       + (f"<br>{f['properties']['gestore']}" if f["properties"].get("gestore") else "")
                       + "<br>Non è nell'elenco FER del Comune: probabilmente fuori dai confini comunali"
                       + "<br><i>OpenStreetMap</i>" for f in fv], hoverinfo="text"))


def figura_mappa(df: pd.DataFrame, stati: list[str] | None = None, stile: str = "open-street-map",
                 confine: dict | None = None, osm: dict | None = None):
    """Mappa plotly con i poligoni colorati per stato; un'etichetta col numero dell'elenco comunale.
    Con `osm`, aggiunge sotto gli impianti le linee ad alta tensione e gli altri fotovoltaici di OpenStreetMap."""
    import plotly.graph_objects as go
    centri = list(zip(df.lon_c, df.lat_c))
    if stati is not None:
        df = df[df.stato.isin(stati)]
    fig = go.Figure()
    if osm:
        _tracce_osm(fig, osm, centri)
    if confine:
        g = confine["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        lon, lat = [], []
        for poly in polys:
            for c in poly[0]:
                lon.append(c[0]); lat.append(c[1])
            lon.append(None); lat.append(None)
        fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", line=dict(color="#37474f", width=2),
                                    name="Confine comunale", hoverinfo="skip"))
    for stato, colore in COLORI_STATO.items():
        d = df[(df.stato == stato) & (df.geometria == "Polygon")]
        if d.empty:
            continue
        lon, lat, testi = [], [], []
        for r in d.itertuples():
            lon += r.lon + [None]; lat += r.lat + [None]
        fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", fill="toself", fillcolor=_rgba(colore, 0.55),
                                    line=dict(color=colore, width=2), name=stato, hoverinfo="skip",
                                    legendgroup=stato))
    # punti centrali: etichette e testo al passaggio del mouse
    for stato, colore in COLORI_STATO.items():
        d = df[(df.stato == stato) & ((df.geometria == "Point") | (df.ha_mappa.fillna(0) >= 0.5))]
        if d.empty:
            continue
        hover = [
            f"<b>{('N. ' + r.n + ' · ') if r.n else ''}{_a_capo(r.nome, 50)}</b><br>"
            f"{r.tipo_esteso} · {r.stato}"
            + (f" · {_mw(r.mw)} MW" if r.mw is not None and pd.notna(r.mw) else "")
            + (f"<br>{_a_capo(r.societa)}" if r.societa else "")
            + (f" · {_a_capo(r.localizzazione)}" if r.localizzazione else "")
            + (f"<br>Superficie: {_mw(r.ha_comune)} ha (elenco comunale)" if r.ha_comune is not None and pd.notna(r.ha_comune) else "")
            + (f"<br>{_a_capo(r.titolo)}" if r.titolo else "")
            + (f"<br>Ente: {_a_capo(r.ente)}" if r.ente else "")
            + (f"<br><i>Nota:</i> {_a_capo(r.nota)}" if r.nota else "")
            + f"<br><i>Compensazione:</i> {_a_capo(r.compensazione)}"
            for r in d.itertuples()]
        fig.add_trace(go.Scattermap(
            lon=d.lon_c, lat=d.lat_c, mode="markers+text", text=d.n, textposition="middle center",
            textfont=dict(size=12, color="black"),
            marker=dict(size=[20 if g == "Point" else 18 for g in d.geometria], color="white", opacity=0.85),
            hovertext=hover, hoverinfo="text", name=stato, legendgroup=stato, showlegend=False))
    fig.update_layout(map=dict(style=stile, center=dict(lat=45.978, lon=13.29), zoom=12.3),
                      margin=dict(l=0, r=0, t=0, b=0), height=620)
    from core.mappe import legende
    return legende(fig, "Impianti dell'elenco comunale", "Rete e altri impianti (OpenStreetMap)" if osm else None)
