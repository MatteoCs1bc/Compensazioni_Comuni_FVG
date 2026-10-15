import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

st.set_page_config(page_title="Compensazioni FER · FVG", page_icon="⚡", layout="wide")

P = "pagine"
pg = st.navigation({
    "": [st.Page(f"{P}/home.py", title="Inizio", icon=":material/home:", default=True)],
    "Per il Comune": [
        st.Page(f"{P}/progetto.py", title="Il mio progetto", icon=":material/folder_open:"),
        st.Page(f"{P}/calcolatore.py", title="Quanto vale", icon=":material/calculate:"),
        st.Page(f"{P}/iter.py", title="Che iter è", icon=":material/route:"),
        st.Page(f"{P}/convenzione.py", title="La convenzione", icon=":material/contract:"),
        st.Page(f"{P}/investire.py", title="Come investirle", icon=":material/savings:"),
        st.Page(f"{P}/fondo.py", title="Fondo per i cittadini", icon=":material/volunteer_activism:"),
    ],
    "Per le imprese": [
        st.Page(f"{P}/impresa.py", title="Sono un'impresa", icon=":material/business:"),
    ],
    "Per tutti": [
        st.Page(f"{P}/misure.py", title="Catalogo delle misure", icon=":material/menu_book:"),
        st.Page(f"{P}/quadro.py", title="Quadro FVG", icon=":material/map:"),
        st.Page(f"{P}/casi.py", title="Casi FVG", icon=":material/folder_open:"),
        st.Page(f"{P}/pavia.py", title="Pavia di Udine", icon=":material/location_city:"),
    ],
    "Per i cittadini": [
        st.Page(f"{P}/perche.py", title="Perché servono", icon=":material/bolt:"),
    ],
}, expanded=True)
from core.progetto import riepilogo_sidebar

pg.run()
# dopo la pagina: così il file salvato contiene anche le modifiche appena fatte
riepilogo_sidebar()
