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
a, b_ = st.columns(2)
with a:
    st.subheader("Sono un Comune")
    st.markdown(
        "- **Quanto vale**: il calcolatore con tutti i metodi affiancati\n"
        "- **Che iter è**: chi decide, in che tempi, dove interviene il Comune *(in arrivo)*\n"
        "- **La convenzione**: le clausole da pretendere *(in arrivo)*\n"
        "- **Come investirle**: catalogo di interventi ammessi *(in arrivo)*"
    )
    st.page_link("pagine/calcolatore.py", label="Apri il calcolatore", icon=":material/calculate:")
with b_:
    st.subheader("Sono un cittadino")
    st.markdown(
        "- **Perché servono** eolico, batterie e grandi impianti per abbassare le bollette *(in arrivo)*\n"
        "- **Quadro FVG**: come sta la rete nel mio comune, quali progetti ci sono\n"
        "- **Casi FVG**: cosa hanno ottenuto altri Comuni"
    )
    st.page_link("pagine/quadro.py", label="Apri il quadro regionale", icon=":material/map:")
