"""Database delle misure di compensazione (data/investimenti/misure.csv)."""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PERCORSO = ROOT / "data" / "investimenti" / "misure.csv"

FASCE = [(0, 10_000, "fino a 10.000 €"), (10_000, 50_000, "10.000–50.000 €"),
         (50_000, 250_000, "50.000–250.000 €"), (250_000, float("inf"), "oltre 250.000 €")]
AMMISSIBILITA = ["Sicura", "Da verificare", "Esclusa"]
IMPEGNO = ["Basso", "Medio", "Alto"]

# id del vecchio catalogo (v0.2) che restano validi: i progetti salvati si ricaricano senza perdite
ID_STORICI = {"fv_edifici", "accumulo_edificio", "cer", "led", "pdc", "isolamento", "ricarica", "bosco", "siepi",
              "rinaturalizzazione", "monitoraggio", "scuole"}
SUGGERITE = ["fv_edifici", "cer", "siepi", "monitoraggio"]


def fascia(costo: float) -> str:
    for lo, hi, nome in FASCE:
        if lo <= costo < hi:
            return nome
    return FASCE[-1][2]


def carica(percorso: Path = PERCORSO) -> pd.DataFrame:
    d = pd.read_csv(percorso, keep_default_na=False)
    for c in ("costo_unitario_min", "costo_unitario_max", "costo_unitario", "quantita_tipica"):
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
    d["costo_tipico"] = d["costo_unitario"] * d["quantita_tipica"]
    d["fascia"] = [fascia(c) if a != "Esclusa" else "—" for c, a in zip(d.costo_tipico, d.ammissibilita)]
    d["beneficiari_lista"] = d["beneficiari"].str.split("; ")
    return d


def filtra(d: pd.DataFrame, ambiti=None, beneficiari=None, modalita=None, fasce=None, impegno=None,
           ammissibilita=None, testo: str = "") -> pd.DataFrame:
    m = pd.Series(True, index=d.index)
    if ambiti:
        m &= d.ambito.isin(ambiti)
    if beneficiari:
        m &= d.beneficiari_lista.apply(lambda b: any(x in b for x in beneficiari))
    if modalita:
        m &= d.modalita.isin(modalita)
    if fasce:
        m &= d.fascia.isin(fasce)
    if impegno:
        m &= d.impegno_uffici.isin(impegno)
    if ammissibilita:
        m &= d.ammissibilita.isin(ammissibilita)
    if testo:
        t = testo.lower()
        m &= (d.misura.str.lower().str.contains(t, regex=False) | d.descrizione.str.lower().str.contains(t, regex=False))
    return d[m]


def excel(d: pd.DataFrame) -> bytes:
    cols = ["id", "ambito", "misura", "descrizione", "categoria_dm2010", "beneficiari", "modalita", "unita",
            "costo_unitario_min", "costo_unitario_max", "costo_unitario", "quantita_tipica", "costo_tipico", "fascia",
            "impegno_uffici", "ammissibilita", "nota_ammissibilita", "cofinanziamenti_e_cumulabilita", "indicatore",
            "esempi_e_fonti"]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        d[cols].to_excel(xw, sheet_name="Misure", index=False)
        ws = xw.sheets["Misure"]
        larghezze = {"A": 22, "B": 22, "C": 50, "D": 70, "E": 24, "F": 34, "G": 22, "P": 16, "Q": 60, "R": 60, "T": 50}
        for col, w in larghezze.items():
            ws.column_dimensions[col].width = w
        ws.freeze_panes = "D2"
        ws.auto_filter.ref = ws.dimensions
    return buf.getvalue()
