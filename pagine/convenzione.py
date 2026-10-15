import streamlit as st

from core.convenzione_docx import bozza
from core.dati import euro
from core.iter import NOMI_REGIME
from core.progetto import checkbox, esito, progetto

p = progetto()
st.title("La convenzione")
st.markdown("Spunta le clausole che vuoi inserire: la bozza Word si compila con i dati del progetto, "
            "la compensazione calcolata e gli interventi scelti in «Come investirle».")
if not p["compilato"]:
    st.info("Nessun progetto inserito: la bozza avrà dei campi [●] da completare.", icon=":material/info:")
    st.page_link("pagine/progetto.py", label="Vai a «Il mio progetto»", icon=":material/add_circle:")

VOCI = [
    ("importo", "Importo e base di calcolo scritti", "Cifra in euro e metodo di calcolo, in allegato."),
    ("annuale", "Quote annue per tutta la vita dell'impianto", "Non solo una tantum: ad Atlas Solar 1 sono rimasti 180.000 € una tantum."),
    ("rivalutazione", "Rivalutazione annua", "Importi aggiornati con l'indice ISTAT."),
    ("garanzia", "Garanzia fideiussoria", "A copertura delle compensazioni, distinta da quella per lo smantellamento."),
    ("subentro", "Subentro", "Gli obblighi passano a chi compra l'impianto o la società."),
    ("rendiconto", "Rendiconto annuale pubblico", "Cosa è stato versato e realizzato, ogni anno."),
    ("penali", "Penali", "Per ritardi o mancata realizzazione."),
    ("interventi", "Elenco degli interventi allegato", "Modificabile di comune accordo."),
    ("prima_lavori", "Firma prima dell'inizio lavori", "Senza convenzione firmata non si parte."),
    ("comitato", "Comitato di monitoraggio", "Comune, impresa e un rappresentante dei cittadini verificano ogni anno cosa è stato fatto."),
    ("modifica", "Procedura per modificare gli interventi", "Come cambiare l'elenco senza riaprire tutto: proposta, parere del comitato, delibera."),
]
c1, c2 = st.columns([3, 2])
with c1:
    scelte = {k: checkbox(f"**{t}** — {d}", f"cv_{k}", default=True) for k, t, d in VOCI}
with c2:
    with st.container(border=True):
        realizza = st.radio("Chi realizza gli interventi", ["Comune", "Proponente"], horizontal=True,
                            help="Comune: più controllo sulle scelte, serve capacità di progettare. Proponente: meno carico per gli uffici.")
        st.metric("Compensazione calcolata", euro(p.get("compensazione_eur")) if p.get("compensazione_eur") else "non calcolata")
        if not p.get("compensazione_eur"):
            st.page_link("pagine/calcolatore.py", label="Calcolala", icon=":material/calculate:")
        interventi = st.session_state.get("piano_interventi", [])
        st.caption(f"Interventi nel piano: {len(interventi)}")

opz = dict(scelte, realizza=realizza)
if p["compilato"]:
    opz["titolo"] = NOMI_REGIME[esito().regime]
opz["fondo"] = any(x.get("id") == "fondo_cittadini" for x in interventi)
if opz["fondo"]:
    st.info("Il piano contiene il **fondo per i cittadini**: la bozza aggiunge un articolo che vincola le somme a un programma "
            "di efficienza energetica per le famiglie, condizione perché il fondo sia ammissibile.", icon=":material/volunteer_activism:")
if p.get("calcolo_testo"):
    opz["calcolo"] = p["calcolo_testo"] + " Parametri e metodo come da strumento «Compensazioni FER · FVG» (metodo Agenzia per l'Energia FVG)."
st.download_button("Scarica la bozza di convenzione (.docx)", data=bozza(p, opz, interventi if scelte["interventi"] else []),
                   file_name=f"bozza_convenzione_{(p.get('comune') or 'comune').replace(' ', '_')}.docx",
                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                   type="primary", icon=":material/download:")
st.caption("Bozza di lavoro costruita confrontando la bozza Atlas Solar 1 (2022) e il decreto AU 43585/2024. "
           "Va verificata dal Segretario comunale.")
