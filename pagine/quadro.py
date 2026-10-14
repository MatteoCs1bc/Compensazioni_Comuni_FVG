import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.dati import comuni_indicatori, geo, num, tabella

st.title("Quadro FVG: dove il territorio è più carico")
st.markdown(
    "Ogni comune con i dati pubblici disponibili: **pressione sulla rete**, **inversioni di flusso**, "
    "**accumuli** e **grandi impianti fotovoltaici** autorizzati. I numeri della rete riguardano "
    "l'area servita dalla cabina primaria, che spesso va oltre i confini del comune."
)

c = comuni_indicatori()
import os
MAPPA = os.environ.get("MAPPA_STILE", "carto-positron")  # "white-bg" se le tile non sono raggiungibili
INDICATORI = {
    "MW richiesti sulla rete che serve il comune": ("mw_richiesti_sulle_aree", "MW"),
    "Accumuli (BESS) in autorizzazione unica nel comune": ("bess_mw", "MW"),
    "FV/agrivoltaico ≥1 MW autorizzati 2025–26 (progetti)": ("au_fv_n", "progetti"),
    "Sezioni di cabina con inversione di flusso": ("sezioni_invertite", "sezioni"),
    "Progetti FER in autorizzazione localizzati nel comune": ("progetti_nel_comune", "progetti"),
}
scelta = st.selectbox("Cosa mostrare sulla mappa", list(INDICATORI))
col, unita = INDICATORI[scelta]

fig = px.choropleth_map(
    c, geojson=geo("comuni_fvg"), locations="comune", featureidkey="properties.comune", color=col,
    color_continuous_scale="Blues", map_style=MAPPA, zoom=7.4, center={"lat": 46.1, "lon": 13.05},
    opacity=0.75, hover_name="comune",
    hover_data={"comune": False, col: ":.1f", "stato_indicativo": True},
    labels={col: unita, "stato_indicativo": "Rete"},
)
if col == "bess_mw":
    b = tabella("bess_progetti.csv")
    b = b[b.conta_nel_totale]
    fig.add_trace(go.Scattermap(lat=b.lat, lon=b.lon, mode="markers",
                                marker=dict(size=(b.mw.fillna(5) ** 0.5) * 2.2, color="#eb6834", opacity=0.85),
                                text=b.progetto + " · " + b.mw.round(1).astype(str) + " MW · " + b.stato,
                                hoverinfo="text", name="Progetti BESS"))
fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar=dict(title=unita))
st.plotly_chart(fig, use_container_width=True)

st.subheader("La scheda del mio comune")
nome = st.selectbox("Comune", sorted(c.comune), index=sorted(c.comune).index("Pavia Di Udine"))
r = c[c.comune == nome].iloc[0]
k = st.columns(5)
k[0].metric("Superficie", f"{num(r.km2_comune, 1)} km²")
k[1].metric("Cabine primarie che lo servono", int(r.aree_cabina),
            help="Se più di una, una CER comunale non copre tutto il territorio")
k[2].metric("MW richiesti sull'area di rete", num(r.mw_richiesti_sulle_aree, 0))
k[3].metric("Accumuli (portale regionale)", f"{num(r.bess_mw, 0)} MW", help="Pratiche BESS sul portale regionale RIS_ENERG; i registri comunali possono includerne altre")
k[4].metric("FV ≥1 MW autorizzati 2025–26", int(r.au_fv_n))
st.markdown(
    f"- Stato della rete (lettura indicativa): **{r.stato_indicativo}** · sezioni invertite: {int(r.sezioni_invertite)} "
    f"(di cui oltre il 5% del tempo: {int(r.sezioni_oltre_5pct)})\n"
    f"- Comune diviso tra più cabine: **{'sì' if r.comune_diviso else 'no'}**\n"
    f"- Opposizione locale censita: **{'sì' if r.opposizione_censita else 'nessuna nel censimento'}**"
)
if nome == "Pavia Di Udine":
    st.page_link("pagine/pavia.py", label="Apri la scheda completa di Pavia di Udine", icon=":material/location_city:")

with st.expander("Progetti nel comune"):
    pp = tabella("progetti_regionali_con_comune.csv")
    pp = pp[pp.comune == nome][["categoria", "nome", "potenza_mw", "superficie_ha", "stato"]]
    st.dataframe(pp.sort_values("potenza_mw", ascending=False), hide_index=True, use_container_width=True)

with st.expander("Opposizioni locali censite in regione"):
    st.dataframe(tabella("opposizioni_locali.csv"), hide_index=True, use_container_width=True)

st.caption(
    "Fonti: aree delle cabine primarie (distributori, 30/09/2025); inversioni di flusso e-distribuzione 2025 "
    "(pubbl. 28/02/2026); progetti e accumuli dal portale regionale RIS_ENERG; FV ≥1 MW dalla ricognizione "
    "dei decreti sul BUR 2025–26. **La capacità residua di rete cabina per cabina non è pubblica**: nessun "
    "dato qui indica i MW ancora liberi. La colonna «stato» della rete è una lettura indicativa, non ufficiale."
)
