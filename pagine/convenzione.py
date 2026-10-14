import streamlit as st

st.title("La convenzione")
st.warning("Pagina in costruzione: arriverà uno schema di convenzione scaricabile. Intanto, la checklist.")
st.markdown("**Le clausole da pretendere** (dal confronto tra la bozza Atlas Solar 1 e il decreto finale)")
voci = [
    ("Importo e base di calcolo scritti", "Cifra in euro e metodo con cui è stata calcolata (vedi «Quanto vale»)."),
    ("Durata pari alla vita dell'impianto", "Non solo una tantum: misure o quote annue per tutta la vita utile."),
    ("Rivalutazione", "Aggiornamento annuo degli importi (es. indice ISTAT)."),
    ("Garanzia fideiussoria", "A copertura degli impegni di compensazione, distinta da quella per lo smantellamento."),
    ("Subentro", "Gli obblighi passano a chi acquista l'impianto o la società."),
    ("Chi realizza le opere", "Il proponente o il Comune; se il Comune, tempi e modalità di pagamento."),
    ("Elenco degli interventi", "Allegato con interventi, tempi, costi; possibilità di modificarlo nel tempo."),
    ("Monitoraggio e rendiconto annuale", "Report pubblico su cosa è stato fatto."),
    ("Penali", "Per ritardi o mancata realizzazione."),
    ("Firma prima dell'inizio lavori", "Come nell'AU Atlas: senza convenzione firmata non si parte."),
]
for t, d in voci:
    st.checkbox(f"**{t}** — {d}", key=t)
