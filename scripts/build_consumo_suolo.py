"""Estrae dai file ISPRA 2026 i dati di consumo di suolo dei comuni del Friuli Venezia Giulia.

Uso:
    python scripts/build_consumo_suolo.py consumo_suolo_2026_dati_principali.xlsx potenziale_recupero_2026.xlsx

Fonte: Munafò M. (a cura di), 2026, Consumo di suolo, ecosistemi urbani e stato del territorio. Edizione 2026,
Report ambientali SNPA 50/2026 (licenza CC BY 4.0). I file sono nel Drive: Italy › consumo di suolo › 2026-10.

Scrive data/territorio/consumo_suolo_fvg_2026.csv: una riga per comune FVG più la riga «Friuli-Venezia Giulia».
"""
import sys
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "territorio" / "consumo_suolo_fvg_2026.csv"
REGIONE = "Friuli-Venezia Giulia"


def _foglio(path, nome):
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)[nome]
    righe = list(ws.iter_rows(values_only=True))
    return pd.DataFrame(righe[1:], columns=righe[0])


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main(principali: str, recupero: str):
    com = _foglio(principali, "Comuni_2006_2025")
    com = com[com.Nome_Regione == REGIONE].copy()
    reg = _foglio(principali, "Regioni_2006_2025")
    reg = reg[reg.Nome_Regione == REGIONE].copy()
    reg.insert(0, "Nome_Comune", REGIONE)
    reg["PRO_COM"] = 0
    df = pd.concat([com, reg], ignore_index=True)

    out = pd.DataFrame({"pro_com": df.PRO_COM.astype(int), "comune": df.Nome_Comune,
                        "provincia": df.get("Nome_Provincia")})
    for col in df.columns:
        if col.startswith("Incremento netto "):
            periodo = col.split()[2]  # es. 2006-2012
            out[f"netto_{periodo.replace('-', '_')}"] = df[col].map(_num)
    out["ripristino_2024_2025"] = df["Ripristino 2024-2025 [ettari]"].map(_num)
    out["consumato_2025_ha"] = df["Suolo consumato 2025 [ettari]"].map(_num)
    out["consumato_2025_pct"] = df["Suolo consumato 2025 [%]"].map(_num)
    out["superficie_ha"] = (out.consumato_2025_ha / (out.consumato_2025_pct / 100)).round(1)

    rec = _foglio(recupero, "Comuni")
    rec = rec[rec.Nome_Regione == REGIONE]
    tetti = {r.PRO_COM: (_num(r["Potenziale_superficie_minima_disponibile_tetti_per_fotovoltaico [ettari]"]),
                         _num(r["Potenziale_superficie_massima_disponibile_tetti_per_fotovoltaico [ettari]"]))
             for _, r in rec.iterrows()}
    out["tetti_fv_min_ha"] = out.pro_com.map(lambda c: tetti.get(c, (None, None))[0])
    out["tetti_fv_max_ha"] = out.pro_com.map(lambda c: tetti.get(c, (None, None))[1])
    m = out.pro_com == 0
    out.loc[m, "tetti_fv_min_ha"] = out.loc[~m, "tetti_fv_min_ha"].sum()
    out.loc[m, "tetti_fv_max_ha"] = out.loc[~m, "tetti_fv_max_ha"].sum()
    out = out.round(3)
    out.to_csv(OUT, index=False)
    print(f"{len(out) - 1} comuni FVG → {OUT}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
