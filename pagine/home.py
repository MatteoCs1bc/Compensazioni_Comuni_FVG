import streamlit as st

from core.dati import comuni_indicatori, num, tabella

st.title("Compensazioni per gli impianti rinnovabili in Friuli Venezia Giulia")
st.markdown(
    "Uno strumento per **Comuni** e **cittadini**: quanto vale un impianto per il territorio, "
    "come si arriva a una convenzione, come investire le risorse e dove la regione è già più carica."
)

c = comuni_indicatori()
b = tabella("bess_progetti.csv")
au = tabella("au_fv_2025_2026.csv")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Comuni FVG", len(c))
k2.metric("Accumuli (BESS) in autorizzazione unica", f"{num(b[b.conta_nel_totale].mw.sum(), 0)} MW",
          help="Pratiche dal server regionale RIS_ENERG, duplicati rimossi")
k3.metric("FV/agrivoltaico ≥1 MW autorizzati 2025–26", f"{len(au)} progetti",
          help="Ricognizione dai decreti pubblicati sul BUR")
k4.metric("Comuni con inversione di flusso in rete", f"{int(c.flusso_invertito.sum())} su {len(c)}")

st.divider()
a, b_, c_ = st.columns(3)
with a:
    st.subheader("Sono un Comune")
    st.markdown(
        "1. **Il mio progetto**: carica i documenti o inserisci i dati\n"
        "2. **Quanto vale**: scegli la percentuale e vedi il calcolo passo per passo\n"
        "3. **Che iter è**: la mappa del procedimento e cosa fare in ogni fase\n"
        "4. **La convenzione**: le clausole e la bozza Word precompilata\n"
        "5. **Come investirle**: il piano degli interventi dentro il budget, dal catalogo di oltre 100 misure\n"
        "6. **Fondo per i cittadini**: bandi annuali o fondo rotativo, con regolamento e bando scaricabili"
    )
    st.page_link("pagine/progetto.py", label="Inizia dal tuo progetto", icon=":material/add_circle:")
with b_:
    st.subheader("Sono un cittadino")
    st.markdown(
        "- **Perché servono** eolico, batterie e grandi impianti per abbassare le bollette, con i dati 2025\n"
        "- **Quadro FVG**: come sta la rete nel mio comune, quali progetti ci sono\n"
        "- **Casi FVG**: cosa hanno ottenuto altri Comuni"
    )
    st.page_link("pagine/quadro.py", label="Apri il quadro regionale", icon=":material/map:")
with c_:
    st.subheader("Sono un'impresa")
    st.markdown(
        "- Cosa succede se il Comune **non risponde**\n"
        "- La sequenza consigliata: proposta via PEC, sollecito, **atto unilaterale d'obbligo**\n"
        "- I modelli già compilati con il calcolo e il piano"
    )
    st.page_link("pagine/impresa.py", label="Apri la pagina per le imprese", icon=":material/business:")
