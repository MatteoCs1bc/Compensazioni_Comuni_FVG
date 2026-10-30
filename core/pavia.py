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
