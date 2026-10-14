import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.dati import DATA, euro, num

BLU, GRIGIO = "#2a78d6", "#9a9890"


@st.cache_data
def orario():
    h = pd.read_csv(DATA / "prezzi" / "orario_2025.csv", parse_dates=["ts"])
    h["ora"] = h.ts.dt.hour
    return h


h = orario()
st.title("Perché servono eolico, batterie e grandi impianti")
st.markdown(
    "Il prezzo all'ingrosso dell'elettricità, ogni ora, lo fissa **l'impianto più caro che serve per coprire la domanda**. "
    "Quasi sempre è una centrale a **gas**. Più sole, vento e batterie ci sono, meno ore il gas decide il prezzo: "
    "e il prezzo scende. Ecco cosa è successo nel 2025 in Italia, ora per ora."
)

k = st.columns(3)
k[0].metric("Prezzo medio 2025 (PUN)", f"{num(h.pun.mean(), 0)} €/MWh")
k[1].metric("Ore con più del 60% di rinnovabili", f"{num(h[h.ren_sh > 0.6].pun.mean(), 0)} €/MWh", help="Prezzo medio in quelle ore")
k[2].metric("Ore con meno del 30% di rinnovabili", f"{num(h[h.ren_sh < 0.3].pun.mean(), 0)} €/MWh", help="Prezzo medio in quelle ore")

st.subheader("Più rinnovabili nella stessa ora, prezzo più basso")
fasce = pd.cut(h.ren_sh, [0, 0.3, 0.4, 0.5, 0.6, 1.0], labels=["< 30%", "30–40%", "40–50%", "50–60%", "> 60%"])
g = h.groupby(fasce, observed=True).agg(prezzo=("pun", "mean"), ore=("pun", "size")).reset_index()
fig = go.Figure(go.Bar(x=g.ren_sh.astype(str), y=g.prezzo, marker_color=[GRIGIO] * 4 + [BLU], width=0.55,
                       text=[f"{v:.0f}" for v in g.prezzo], textposition="outside",
                       customdata=g.ore, hovertemplate="Quota rinnovabili %{x}<br>%{y:.1f} €/MWh<br>%{customdata} ore<extra></extra>"))
fig.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(title="€/MWh, media 2025", rangemode="tozero"),
                  xaxis=dict(title="Quota di rinnovabili sulla produzione dell'ora"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Il prezzo nelle 24 ore")
prof = h.groupby("ora").agg(pun=("pun", "mean"), ren=("ren_sh", "mean")).reset_index()
fig2 = go.Figure(go.Scatter(x=prof.ora, y=prof.pun, mode="lines+markers", line=dict(color=BLU, width=2), marker=dict(size=8),
                            customdata=(prof.ren * 100).round(0),
                            hovertemplate="Ore %{x}:00<br>%{y:.1f} €/MWh<br>rinnovabili %{customdata}%<extra></extra>"))
mn, mx = prof.loc[prof.pun.idxmin()], prof.loc[prof.pun.idxmax()]
fig2.add_annotation(x=mn.ora, y=mn.pun, text=f"{mn.pun:.0f} €/MWh: c'è il sole", showarrow=True, ay=40)
fig2.add_annotation(x=mx.ora, y=mx.pun, text=f"{mx.pun:.0f} €/MWh: sole tramontato, entra il gas", showarrow=True, ay=-40)
fig2.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10), xaxis=dict(title="Ora del giorno", dtick=2),
                   yaxis=dict(title="€/MWh, media 2025"))
st.plotly_chart(fig2, use_container_width=True)
st.markdown(
    "Di giorno il fotovoltaico abbassa il prezzo; la sera, quando il sole tramonta e la domanda è alta, il gas torna a "
    "fissarlo. **Le batterie** spostano l'energia del giorno alla sera; **l'eolico** produce anche di notte e d'inverno. "
    "Servono entrambi, e in grandi quantità: per questo servono anche impianti grandi."
)

st.subheader("Cosa ci guadagna il mio comune")
c1, c2, c3, c4 = st.columns(4)
mw = c1.number_input("MW installati", 1.0, 500.0, 60.0, 5.0)
ore = c2.number_input("Ore di produzione", 500, 4000, 2000, 100)
prezzo = c3.number_input("Prezzo (€/MWh)", 20.0, 200.0, 80.0, 5.0)
perc = c4.number_input("Percentuale (%)", 1.0, 5.0, 4.0, 0.5)
annuo = mw * ore * prezzo * perc / 100
st.success(f"**{euro(annuo)} all'anno** per il territorio, per tutta la vita dell'impianto. "
           f"Su 25 anni: **{euro(annuo * 25)}**.")
st.caption("Esempio «Ci sarà un bel clima»: 10 pale da 6 MW che producono 2.000 ore l'anno a 80 €/MWh, al 4%, lasciano 384.000 € l'anno.")
st.caption("Fonti: GME (PUN orario 2025), Terna (produzione oraria per fonte 2025); elaborazione su 8.760 ore. "
           "Quota rinnovabili = idroelettrico, fotovoltaico, eolico, geotermico e autoconsumo sulla produzione dell'ora.")
