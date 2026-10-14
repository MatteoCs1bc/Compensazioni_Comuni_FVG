import streamlit as st
import yaml

from core.compensazioni import ImpiantoProduzione
from core.dati import DATA, euro, num, pct, regole

R = regole()
D = R["default_fvg"]
casi = yaml.safe_load(open(DATA / "casi" / "casi.yaml", encoding="utf-8"))

st.title("Casi FVG")
st.markdown("Cosa è successo davvero in alcuni Comuni del Friuli Venezia Giulia, con le fonti.")

st.info(
    "**Le compensazioni non si trovano sul Bollettino Ufficiale.** Dei decreti di autorizzazione unica "
    "per impianti ≥1 MW del 2025–26 il BUR pubblica solo un estratto: gli articoli sulle compensazioni "
    "sono «omissis». Per conoscerle servono il decreto integrale, il verbale della conferenza di servizi "
    "o la convenzione, da chiedere a Regione o Comune."
)

for c in casi:
    with st.container(border=True):
        st.subheader(c["titolo"])
        a, b, d = st.columns(3)
        a.markdown(f"**Tipo**: {c['tipo']}  \n**Potenza**: {num(c['potenza_mw'], 2) + ' MW' if c['potenza_mw'] else '–'}")
        b.markdown(f"**Procedura**: {c['procedura']}  \n**Stato**: {c['stato']}")
        comp = c.get("compensazione_eur")
        d.markdown(f"**Compensazione**: {euro(comp) if comp else 'non definita'}  \n{c['compensazione_descrizione']}")
        if comp and c.get("potenza_mw"):
            imp = ImpiantoProduzione(c["potenza_mw"], D["ore_equivalenti"]["fotovoltaico"], D["prezzo_eur_mwh"], D["vita_utile_anni"])
            rif = imp.proventi_anno * 0.03 * imp.vita_utile_anni
            st.markdown(
                f"Con il metodo Agenzia FVG la cifra di riferimento sarebbe **{euro(rif)}**: "
                f"quella ottenuta è il **{pct(comp / (imp.proventi_anno * imp.vita_utile_anni), 2)}** dei proventi "
                f"stimati su {D['vita_utile_anni']} anni (contro il 3%)."
            )
        if c.get("promesso"):
            st.markdown(f"**Promesso all'inizio**: {c['promesso']}")
        st.markdown("**Cosa insegna**\n" + "\n".join(f"- {x}" for x in c["lezioni"]))
        st.caption("Fonti: " + "; ".join(c["fonti"]))
        if c["id"] == "pavia_di_udine":
            st.page_link("pagine/pavia.py", label="Apri la scheda di Pavia di Udine", icon=":material/location_city:")
