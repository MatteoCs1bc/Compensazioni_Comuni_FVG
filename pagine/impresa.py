import pandas as pd
import streamlit as st

from core.dati import euro
from core.impresa_docx import atto_unilaterale, proposta, sollecito
from core.iter import NOMI_REGIME, TIPI
from core.progetto import esito, progetto

p = progetto()
st.title("Sono un'impresa")
st.markdown(
    "Le compensazioni non sono un favore al Comune: sopra 1 MW sono un **obbligo**, e un decreto senza compensazioni in "
    "FVG è un decreto contestabile. Questa pagina spiega cosa succede se il Comune non risponde e come mettere gli impegni "
    "per iscritto in modo che siano certi e verificabili per tutti."
)
if not p["compilato"]:
    st.info("Inserisci il progetto per avere i modelli già compilati.", icon=":material/info:")
    st.page_link("pagine/progetto.py", label="Vai a «Il mio progetto»", icon=":material/add_circle:")
else:
    e = esito()
    st.success(f"**{p['nome']}** · {TIPI[p['tipo']]} · {p['potenza_mw']:g} MW · {NOMI_REGIME[e.regime]}  \n{e.compensazione}",
               icon=":material/business:")
    if not p.get("compensazione_eur"):
        st.page_link("pagine/calcolatore.py", label="Calcola prima la compensazione: i modelli la riportano", icon=":material/calculate:")

st.header("Se il Comune non risponde")
st.table(pd.DataFrame([
    ("Attività libera", "Nessun obbligo di compensazione: non succede nulla."),
    ("PAS (decide il Comune)", "Il programma 1–3% è parte della domanda. Dopo 30 giorni vale il silenzio-assenso: "
                               "l'impresa resta vincolata a quanto ha proposto."),
    ("Autorizzazione unica", "Il Comune assente in conferenza è considerato d'accordo senza condizioni. Le compensazioni le "
                             "fissa comunque la conferenza (1–4%, in FVG almeno il 3%)."),
    ("Convenzione prima dei lavori", "Se il decreto la richiede e il Comune non firma, il cantiere rischia di non partire: "
                                     "è qui che il silenzio del Comune pesa sull'impresa."),
], columns=["Procedura", "Cosa succede"]).set_index("Procedura"))

st.header("La sequenza consigliata")
passi = [
    ("1 · Proposta scritta via PEC", "Calcolo, interventi e schema di convenzione, con un termine di 30 giorni per rispondere. "
                                    "Toglie al Comune l'argomento «non ci hanno proposto niente»."),
    ("2 · Sollecito con copia alla Regione", "Dopo 30 giorni senza risposta. La Regione, che guida il procedimento, è informata."),
    ("3 · Atto unilaterale d'obbligo", "Se il silenzio continua, l'impresa firma da sola i propri impegni (importi, interventi, "
                                       "tempi, garanzie) e li deposita in Comune e in Regione. Se basti a sostituire la "
                                       "convenzione richiesta dal decreto va verificato con la Regione caso per caso."),
    ("4 · Coinvolgimento dei cittadini documentato", "In FVG, sopra 1 MW, conservare la prova di aver chiesto al Comune un "
                                                     "momento pubblico (L.R. 2/2025, art. 5, lett. j)."),
]
for t, x in passi:
    with st.container(border=True):
        st.markdown(f"**{t}**  \n{x}")

st.header("I modelli")
interventi = st.session_state.get("piano_interventi", [])
procedura = NOMI_REGIME[esito().regime] if p["compilato"] else "[procedura]"
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Lettera di proposta**")
    st.caption(f"Compensazione: {euro(p['compensazione_eur']) if p.get('compensazione_eur') else 'da calcolare'} · "
               f"interventi nel piano: {len(interventi)}")
    st.download_button("Scarica (.docx)", proposta(p, procedura, interventi), "proposta_compensazioni.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", icon=":material/download:",
                       key="dl_proposta")
with c2:
    st.markdown("**Sollecito**")
    data_prima = st.date_input("Data della prima PEC", value=None, format="DD/MM/YYYY")
    st.download_button("Scarica (.docx)", sollecito(p, data_prima.strftime("%d/%m/%Y") if data_prima else ""),
                       "sollecito_compensazioni.docx", icon=":material/download:", key="dl_sollecito",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
with c3:
    st.markdown("**Atto unilaterale d'obbligo**")
    gar = st.toggle("Con garanzia fideiussoria", value=True)
    st.download_button("Scarica (.docx)", atto_unilaterale(p, procedura, interventi, gar), "atto_unilaterale_obbligo.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", icon=":material/download:",
                       key="dl_atto")
st.caption("Bozze di lavoro, non pareri legali: farle verificare a un legale prima dell'invio. Il piano degli interventi "
           "si compone nella pagina «Come investirle».")
