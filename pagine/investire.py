import zlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.dati import euro
from core.misure import FASCE, IMPEGNO, SUGGERITE, carica, filtra
from core.progetto import progetto

p = progetto()
D = carica()
AMMESSE = D[D.ammissibilita != "Esclusa"]
INFO = AMMESSE.set_index("id")
COLORI = {"Fonti rinnovabili": "#2a78d6", "Efficienza energetica": "#eb6834",
          "Miglioramento ambientale": "#1baf7a", "Sensibilizzazione": "#eda100"}

st.title("Come investire le compensazioni")
st.markdown("Scegli le misure dal **catalogo** (oltre 100 voci, anche piccole), regola quantità e costi e vedi "
            "subito quanto del budget usi. Il piano finisce nella bozza di convenzione.")
with st.expander("Cosa NON si può fare", icon=":material/block:"):
    for _, r in D[D.ammissibilita == "Esclusa"].iterrows():
        st.markdown(f"- **{r.misura}** — {r.nota_ammissibilita}")

# ------------------------------------------------------------------ budget
st.header("1 · Il budget")
calc = p.get("compensazione_eur") or 0.0
b1, b2 = st.columns(2)
fonte = b1.radio("Da dove parto", ["Compensazione calcolata", "Inserisco io una cifra"], horizontal=True,
                 index=0 if calc else 1)
if fonte == "Compensazione calcolata" and calc:
    budget = calc
    b2.metric("Budget dal calcolatore", euro(budget))
    if p.get("compensazione_annua_eur"):
        b2.caption(f"di cui {euro(p['compensazione_annua_eur'])} all'anno")
elif fonte == "Compensazione calcolata":
    b2.warning("Nessuna compensazione calcolata: inserisci una cifra o passa dal calcolatore.")
    budget = 0.0
else:
    budget = b2.number_input("Budget (€)", min_value=0.0, value=300000.0, step=10000.0)

# ------------------------------------------------------------------ scelta delle misure
st.header("2 · Scegli le misure")
piano = {x["id"]: x for x in st.session_state.get("piano_interventi", []) if x.get("id") in INFO.index}
if "ms_misure" not in st.session_state:
    st.session_state["ms_misure"] = list(piano) if (piano or st.session_state.get("piano_toccato")) else list(SUGGERITE)

with st.container(border=True):
    st.caption("Filtra il catalogo per trovare le misure adatte al tuo Comune, poi aggiungile al piano.")
    f1, f2, f3, f4 = st.columns(4)
    amb = f1.multiselect("Ambito", sorted(AMMESSE.ambito.unique()))
    ben = f2.multiselect("A chi va", sorted({b for l in AMMESSE.beneficiari_lista for b in l}))
    fas = f3.multiselect("Costo tipico", [f[2] for f in FASCE])
    imp = f4.multiselect("Impegno uffici", IMPEGNO)
    solo_sicure = st.toggle("Solo misure ad ammissibilità sicura")
    v = filtra(AMMESSE, amb, ben, None, fas, imp, ["Sicura"] if solo_sicure else None)
    opzioni = list(dict.fromkeys(v.id.tolist() + st.session_state["ms_misure"]))
    scelte = st.multiselect(f"Misure nel piano ({len(v)} disponibili con questi filtri)", opzioni, key="ms_misure",
                            format_func=lambda i: f"{INFO.loc[i, 'misura']} · {INFO.loc[i, 'fascia']}"
                            + (" · da verificare" if INFO.loc[i, "ammissibilita"] == "Da verificare" else ""))
st.session_state["piano_toccato"] = True
st.page_link("pagine/misure.py", label="Apri il catalogo completo con le schede", icon=":material/menu_book:")

# ------------------------------------------------------------------ quantità
st.header("3 · Quantità e costi")
if not scelte:
    st.info("Nessuna misura scelta.")
    st.session_state["piano_interventi"] = []
    st.stop()
st.caption("Costi indicativi: sostituiscili con preventivi o con il prezziario regionale.")
righe = []
for i in scelte:
    r, s = INFO.loc[i], piano.get(i)
    righe.append({"id": i, "Misura": r.misura, "Categoria": r.categoria_dm2010,
                  "Quantità": float(s["q"]) if s else float(r.quantita_tipica), "Unità": r.unita,
                  "€ per unità": float(s["cu"]) if s else float(r.costo_unitario),
                  "Ammissibilità": r.ammissibilita})
chiave = f"ed_piano_{st.session_state.get('n_caricamenti', 0)}_{zlib.crc32('|'.join(scelte).encode())}"
ed = st.data_editor(pd.DataFrame(righe), hide_index=True, use_container_width=True, key=chiave,
                    column_config={"id": None,
                                   "Quantità": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                                   "€ per unità": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.0f €")},
                    disabled=["Misura", "Categoria", "Unità", "Ammissibilità"])
ed["Costo"] = ed["Quantità"] * ed["€ per unità"]
st.session_state["piano_interventi"] = [
    {"id": r["id"], "nome": r["Misura"], "quantita": f"{r['Quantità']:g} {r['Unità']}", "costo": float(r["Costo"]),
     "q": float(r["Quantità"]), "cu": float(r["€ per unità"])} for _, r in ed.iterrows()]

# ------------------------------------------------------------------ piano
st.header("4 · Il piano")
speso = ed["Costo"].sum()
m1, m2, m3 = st.columns(3)
m1.metric("Budget", euro(budget))
m2.metric("Misure scelte", euro(speso))
m3.metric("Restano" if budget >= speso else "Mancano", euro(abs(budget - speso)))
fig = go.Figure()
for cat, g in ed.groupby("Categoria"):
    fig.add_trace(go.Bar(x=[g["Costo"].sum()], y=["Piano"], orientation="h", name=cat, marker_color=COLORI.get(cat, "#9a9890"),
                         marker_line=dict(color="white", width=2), hovertemplate=f"{cat}: %{{x:,.0f}} €<extra></extra>"))
if budget:
    fig.add_vline(x=budget, line_color="#3b3a37", line_dash="dot", annotation_text="budget", annotation_position="top")
fig.update_layout(barmode="stack", height=170, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(tickformat=",.0f"),
                  legend=dict(orientation="h", y=-0.45))
st.plotly_chart(fig, use_container_width=True)
if budget and speso > budget:
    st.warning("Il piano supera il budget: riduci le quantità o cerca cofinanziamenti (vedi le schede).")
n_ver = int((ed["Ammissibilità"] == "Da verificare").sum())
if n_ver:
    st.info(f"{n_ver} {'misura è' if n_ver == 1 else 'misure sono'} «da verificare»: scrivile in modo esplicito nella convenzione e chiedi conferma "
            "all'ufficio regionale o al segretario comunale.")
c1, c2 = st.columns(2)
c1.page_link("pagine/convenzione.py", label="Inserisci il piano nella bozza di convenzione", icon=":material/contract:")
c2.page_link("pagine/fondo.py", label="Progetta il fondo per i cittadini", icon=":material/volunteer_activism:")

st.header("5 · Le schede")
for _, r in ed.iterrows():
    x = INFO.loc[r["id"]]
    with st.expander(f"{x.misura} · {euro(r['Costo'])}"):
        if x.descrizione:
            st.markdown(x.descrizione)
        st.markdown(f"**Costo indicativo**: {euro(x.costo_unitario_min)}–{euro(x.costo_unitario_max)} per {x.unita} · "
                    f"**impegno uffici**: {x.impegno_uffici} · **a chi va**: {x.beneficiari}")
        st.markdown(f"**Ammissibilità ({x.ammissibilita.lower()})**: {x.nota_ammissibilita}")
        if x.cofinanziamenti_e_cumulabilita:
            st.markdown(f"**Cofinanziamenti**: {x.cofinanziamenti_e_cumulabilita}")
        if x.esempi_e_fonti:
            st.caption(x.esempi_e_fonti)
