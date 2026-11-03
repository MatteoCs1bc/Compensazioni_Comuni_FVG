import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.dati import comuni_indicatori, geo, num, tabella
from core.mappe import COLORI_CATEGORIA, STATI_FVG, figura_fvg, osm_fvg, progetti_fvg

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

st.subheader("Rete elettrica, progetti ed esistente")
st.markdown(
    "Le linee ad alta tensione, i progetti del portale regionale e gli impianti già in funzione. "
    "Si vede dove i progetti si addensano: attorno alle stazioni dove arrivano le linee a 220 e 380 kV."
)
pf = progetti_fvg()
cat_sel = st.pills("Tipo di impianto", list(COLORI_CATEGORIA), selection_mode="multi",
                   default=list(COLORI_CATEGORIA), key="fvg_cat")
stati_sel = st.pills("Stato", STATI_FVG, selection_mode="multi", default=STATI_FVG, key="fvg_stati")
LIVELLI = {"Linee AT (132-380 kV)": "linee", "Stazioni e cabine primarie": "cabine",
           "Aree di cabina primaria (MW richiesti)": "aree", "Cabine secondarie (circa 7.000)": "secondarie",
           "Centrali esistenti": "centrali", "Fotovoltaico a terra esistente": "fv_osm"}
liv_sel = st.pills("Rete ed esistente (OpenStreetMap e dati di rete)", list(LIVELLI), selection_mode="multi",
                   default=["Linee AT (132-380 kV)", "Stazioni e cabine primarie", "Centrali esistenti",
                            "Fotovoltaico a terra esistente"], key="fvg_livelli")
st.plotly_chart(figura_fvg(pf, osm_fvg(), cat_sel or [], stati_sel or [], {LIVELLI[x] for x in liv_sel or []},
                           os.environ.get("MAPPA_STILE_FVG", "open-street-map")),
                use_container_width=True, key="fvg_rete", config={"scrollZoom": True, "displaylogo": False})
vis = pf[pf.categoria.isin(cat_sel or []) & pf.stato.isin(stati_sel or [])]
st.caption(
    f"{len(vis)} impianti selezionati, {num(vis.potenza_mw.sum(), 0)} MW. La dimensione del punto cresce con la potenza; "
    "il bordo scuro indica gli impianti già realizzati. Fonti: portale regionale RIS_ENERG (progetti), registro BESS del tool "
    "(accumuli, con le potenze corrette), aree di cabina primaria e richieste di connessione (e-distribuzione/GSE), "
    "© OpenStreetMap contributors, ODbL (linee, cabine, centrali e fotovoltaico a terra, estrazioni del 03/11/2026). "
    "Le cabine secondarie vengono in gran parte dalla cartografia tecnica regionale; su OpenStreetMap mancano molti "
    "impianti recenti e le linee a media tensione. L'inversione di flusso è agganciata alla cabina primaria più vicina "
    "entro 3 km."
)

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

via = tabella("registro_via_fvg.csv").fillna("")
via_comune = via[via.comuni.str.lower().str.contains(nome.lower())]
if len(via_comune):
    with st.expander(f"Procedure di VIA che toccano il comune ({len(via_comune)})"):
        for x in via_comune.itertuples():
            st.markdown(f"**{x.progetto}** · {x.tecnologia} · {x.potenza}  \n{x.atti_e_stato}  \n"
                        f"Ruolo del comune: {x.comuni}")

with st.expander("Opposizioni locali censite in regione"):
    st.dataframe(tabella("opposizioni_locali.csv"), hide_index=True, use_container_width=True)

st.caption(
    "Fonti: aree delle cabine primarie (distributori, 30/09/2025); inversioni di flusso e-distribuzione 2025 "
    "(pubbl. 28/02/2026); progetti e accumuli dal portale regionale RIS_ENERG; FV ≥1 MW dalla ricognizione "
    "dei decreti sul BUR 2025–26. **La capacità residua di rete cabina per cabina non è pubblica**: nessun "
    "dato qui indica i MW ancora liberi. La colonna «stato» della rete è una lettura indicativa, non ufficiale."
)

st.header("Registro delle VIA in FVG")
st.markdown(
    "Procedure di valutazione di impatto ambientale raccolte nella documentazione «VIA FVG»: una riga per progetto, con "
    "gli atti principali e la posizione degli enti locali quando risulta dai documenti. **Attenzione**: le "
    "*compensazioni ambientali* della VIA (siepi, prati, boschi) non sono le *compensazioni territoriali* al Comune "
    "previste dal DM 10/9/2010 e dalla L.R. 2/2025, che si fissano nell'autorizzazione unica."
)
f1, f2, f3 = st.columns(3)
cat = f1.multiselect("Categoria", sorted(via.categoria.unique()), default=["Rinnovabili"])
tec = f2.multiselect("Tecnologia", sorted(via.tecnologia.unique()))
cerca = f3.text_input("Comune o progetto contiene")
v = via[via.categoria.isin(cat or via.categoria.unique())]
if tec:
    v = v[v.tecnologia.isin(tec)]
if cerca:
    s = cerca.lower()
    v = v[v.comuni.str.lower().str.contains(s) | v.progetto.str.lower().str.contains(s)]
st.dataframe(v.drop(columns=["id"]).rename(columns={
    "progetto": "Progetto", "categoria": "Categoria", "tecnologia": "Tecnologia", "potenza": "Potenza", "comuni": "Comuni",
    "proponente": "Proponente", "procedura": "Procedura", "atti_e_stato": "Atti e stato",
    "posizione_enti_locali": "Posizione degli enti locali", "compensazioni": "Compensazioni",
    "rilevanza_pavia": "Rilevanza per Pavia di Udine", "documenti_cartella": "Documenti"}),
    hide_index=True, use_container_width=True)
st.markdown(
    "- In tutti i pareri regionali sulle VIA statali in area agricola la Giunta chiede al Ministero di **limitare l'uso "
    "dei terreni agricoli al solo agrivoltaico avanzato** (comunicazione n. 291 del 07/03/2025).\n"
    "- Nessuna procedura fissa importi per i Comuni: dove se ne parla (Basiliano), il proponente rinvia "
    "all'autorizzazione unica."
)
st.caption(f"{len(via)} procedure dalla documentazione «VIA FVG» (Drive, novembre 2026); «n.d.» = dato non presente "
           "nei documenti letti. Lettura per estratti: verificare sugli atti prima dell'uso ufficiale.")
