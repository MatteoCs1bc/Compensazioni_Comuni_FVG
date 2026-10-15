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
