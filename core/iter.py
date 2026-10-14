"""Regime autorizzativo, VIA e compensazioni applicabili a un progetto.

Schema semplificato del D.Lgs. 190/2024 (TU FER, testo coordinato v7), Allegati A, B, C.
Le soglie sono in data/regole/iter.yaml; qui solo la logica.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

TIPI = {
    "fv_edificio": "Fotovoltaico su edifici o coperture",
    "fv_terra": "Fotovoltaico a terra",
    "agrivoltaico": "Agrivoltaico",
    "fv_flottante": "Fotovoltaico flottante",
    "eolico": "Eolico",
    "bess": "Accumulo (BESS) autonomo",
    "bess_asservito": "Accumulo (BESS) collegato a un impianto da autorizzare",
}
AREE = {
    "idonea": "Area idonea (L.R. 2/2025, art. 2)",
    "industriale": "Area industriale, artigianale o commerciale, discarica o cava",
    "impianto_esistente": "Dentro un impianto industriale o di produzione esistente",
    "ordinaria": "Area ordinaria (né idonea né non idonea)",
    "non_idonea": "Area non idonea",
    "non_so": "Non lo so ancora",
}


def carica_iter() -> dict:
    with open(ROOT / "data" / "regole" / "iter.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class Esito:
    regime: str            # libera | pas | au_regionale | au_statale
    riferimento: str
    via: str
    compensazione: str
    perc_min: float
    perc_max: float
    note: list


def determina_regime(tipo: str, mw: float, area: str) -> Esito:
    note = []
    if area == "non_so":
        note.append("Area non indicata: il regime è stimato come area ordinaria. Verificare su Eagle.fvg.")
        area = "ordinaria"
    if area == "non_idonea":
        note.append("In area non idonea il progetto non è vietato, ma la valutazione è più severa e l'esito più incerto.")

    r, rif = "au_regionale", "All. C, sez. I"
    if tipo == "fv_edificio":
        r, rif = ("libera", "All. A, sez. I, lett. a-b") if mw < 12 else ("pas", "All. B, sez. I, lett. a")
        if mw >= 12:
            note.append("Sopra 12 MW su edifici: verificare caso per caso.")
    elif tipo in ("fv_terra", "agrivoltaico"):
        if tipo == "agrivoltaico" and mw < 5:
            r, rif = "libera", "All. A, sez. I, lett. e (agrivoltaico che garantisce la continuità agricola)"
        elif area == "industriale":
            r, rif = (("libera", "All. A, sez. I, lett. c") if mw < 5 else
                      ("pas", "All. B, sez. I, lett. d") if mw <= 15 else ("au_regionale", "All. C, sez. I, lett. a"))
        elif area == "idonea":
            r, rif = ("pas", "All. B, sez. I, lett. b (area idonea, < 12 MW)") if mw < 12 else ("au_regionale", "All. C, sez. I, lett. a")
        else:
            r, rif = ("pas", "All. B, sez. I, lett. f (fino a 1 MW)") if mw <= 1 else ("au_regionale", "All. C, sez. I, lett. a")
        if mw > 300:
            r, rif = "au_statale", "All. C, sez. II"
    elif tipo == "fv_flottante":
        r, rif = ("pas", "All. B, sez. I, lett. e") if mw < 10 else ("au_regionale", "All. C, sez. I")
        note.append("Su bacini artificiali senza vincoli e con copertura < 20% sotto 10 MW può bastare l'attività libera (All. A, lett. c-bis).")
    elif tipo == "eolico":
        if mw <= 0.02:
            r, rif = "libera", "All. A, sez. I, lett. h-i"
        elif mw < 0.06:
            r, rif = "pas", "All. B, sez. I, lett. g"
        elif mw <= 300:
            r, rif = "au_regionale", "All. C, sez. I, lett. c"
        else:
            r, rif = "au_statale", "All. C, sez. II"
    elif tipo == "bess":
        if mw <= 10:
            r, rif = "libera", "All. A, sez. I, lett. t"
        elif area in ("impianto_esistente",):
            r, rif = "pas", "All. B, sez. I, lett. aa"
        elif mw <= 200:
            r, rif = "au_regionale", "All. C, sez. I, lett. u"
        else:
            r, rif = "au_statale", "All. C, sez. II, lett. p (MASE)"
        note.append("Molte autorizzazioni BESS in FVG (es. Pavia di Udine) sono state rilasciate dal Ministero con le regole precedenti al TU FER.")
    elif tipo == "bess_asservito":
        r, rif = "au_regionale", "All. C, sez. I, lett. t (insieme all'impianto)"

    via = valuta_via(tipo, mw, area)
    if r == "libera":
        comp, lo, hi = "Nessun obbligo: si può proporre un accordo volontario.", 0.0, 0.0
    elif r == "pas":
        if mw > 1:
            comp, lo, hi = "Programma di compensazioni obbligatorio: 1–3% del valore della produzione nella vita utile (art. 8, c. 4, lett. m).", 0.01, 0.03
        else:
            comp, lo, hi = "Sotto 1 MW non c'è obbligo: accordo volontario possibile.", 0.0, 0.0
    else:
        if mw > 1:
            comp, lo, hi = ("Compensazioni fissate in conferenza di servizi: 1–4% (TU FER, art. 9, c. 10, lett. d); "
                            "in FVG almeno il 3% dei proventi (L.R. 2/2025, art. 5, lett. i)."), 0.03, 0.04
        else:
            comp, lo, hi = "Compensazioni 1–4% fissate in conferenza di servizi (TU FER, art. 9).", 0.01, 0.04
    if tipo in ("bess", "bess_asservito") and r != "libera":
        comp += " Per gli accumuli la base di calcolo non è definita: si usano i metodi di prassi."
    return Esito(r, rif, via, comp, lo, hi, note)


def valuta_via(tipo: str, mw: float, area: str) -> str:
    if tipo in ("fv_terra", "agrivoltaico", "fv_flottante"):
        if mw > 10:
            return "Probabile VIA statale (MASE) – impianti FV oltre 10 MW"
        if mw > 1:
            return "Probabile verifica di assoggettabilità a VIA regionale"
        return "Di norma nessuna valutazione ambientale"
    if tipo == "eolico":
        if mw > 30:
            return "Probabile VIA statale (MASE) – eolico oltre 30 MW"
        if mw > 1:
            return "Probabile verifica di assoggettabilità a VIA regionale"
        return "Di norma nessuna valutazione ambientale"
    if tipo in ("bess", "bess_asservito"):
        return "Di norma nessuna VIA autonoma; segue la procedura dell'impianto se collegato"
    return "Di norma nessuna valutazione ambientale"


NOMI_REGIME = {"libera": "Attività libera", "pas": "PAS – Procedura abilitativa semplificata",
               "au_regionale": "Autorizzazione unica regionale", "au_statale": "Autorizzazione unica statale (MASE)"}
