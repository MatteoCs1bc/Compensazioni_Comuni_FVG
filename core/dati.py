"""Caricamento dati e formattazione condivisi dalle pagine."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from core.compensazioni import carica_regole

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
T = DATA / "territorio"


def euro(x: float, dec: int = 0) -> str:
    if x is None or pd.isna(x):
        return "–"
    s = f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def num(x: float, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "–"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x: float, dec: int = 1) -> str:
    return num(x * 100, dec) + "%"


@st.cache_data
def regole():
    return carica_regole()


@st.cache_data
def comuni_indicatori() -> pd.DataFrame:
    return pd.read_csv(T / "comuni_indicatori.csv")


@st.cache_data
def geo(nome: str) -> dict:
    return json.load(open(T / "geo" / f"{nome}.geojson", encoding="utf-8"))


@st.cache_data
def tabella(nome: str, cartella: str = "territorio") -> pd.DataFrame:
    return pd.read_csv(DATA / cartella / nome)


def nota_legale():
    st.caption(
        "Strumento informativo, non è consulenza legale. Le percentuali di legge si applicano "
        "secondo il regime autorizzativo dell'impianto; i metodi «di prassi» sono riferimenti di "
        "negoziazione, non obblighi. Verificare sempre il testo vigente delle norme."
    )
