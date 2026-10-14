import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

from core.dati import DATA, euro
from core.progetto import progetto

p = progetto()
CAT = yaml.safe_load(open(DATA / "investimenti" / "catalogo.yaml", encoding="utf-8"))
NOMI_CAT = {"ambiente": "Miglioramento ambientale", "efficienza": "Efficienza energetica",
            "rinnovabili": "Rinnovabili e CER", "sensibilizzazione": "Sensibilizzazione"}

st.title("Come investire le compensazioni")
st.markdown("Le compensazioni vanno spese in **interventi concreti** (DM 10/9/2010, Allegato 2): miglioramento ambientale, "
            "efficienza energetica, rinnovabili, sensibilizzazione. Scegli gli interventi, regola le quantità e vedi "
            "subito quanto del budget usi.")

with st.expander("Cosa NON si può fare", icon=":material/block:"):
    st.markdown("\n".join(f"- {x}" for x in CAT["non_ammessi"]))
    st.markdown("Per portare un beneficio economico alle famiglie la strada legittima è una **comunità energetica** promossa dal Comune.")

st.header("1 · Il budget")
calc = p.get("compensazione_eur") or 0.0
b1, b2 = st.columns(2)
fonte = b1.radio("Da dove parto", ["Compensazione calcolata", "Inserisco io una cifra"], horizontal=True,
                 index=0 if calc else 1)
budget = calc if fonte == "Compensazione calcolata" and calc else b2.number_input("Budget (€)", min_value=0.0, value=500000.0, step=10000.0)
if fonte == "Compensazione calcolata":
    if calc:
        b2.metric("Budget dal calcolatore", euro(budget))
    else:
        b2.warning("Nessuna compensazione calcolata: inserisci una cifra o passa dal calcolatore.")
        budget = 0.0

st.header("2 · Gli interventi")
st.caption(CAT["nota_costi"])
salvato = {x["id"]: x for x in st.session_state.get("piano_interventi", []) if "id" in x}  # piano corrente o caricato da file
righe = []
for x in CAT["interventi"]:
    s_ = salvato.get(x["id"])
    righe.append({"Scegli": (x["id"] in salvato) if salvato else x["id"] in ("fv_edifici", "cer", "siepi", "monitoraggio"),
                  "Intervento": x["nome"], "Tipo": NOMI_CAT[x["categoria"]],
                  "Quantità": float(s_["q"]) if s_ else float(x["quantita_default"]), "Unità": x["unita"],
                  "€ per unità": float(s_["cu"]) if s_ else float(x["costo_unitario"]), "id": x["id"]})
df = pd.DataFrame(righe)
ed = st.data_editor(
    df, hide_index=True, use_container_width=True, key=f"editor_interventi_{st.session_state.get('n_caricamenti', 0)}",
    column_config={"id": None,
                   "Scegli": st.column_config.CheckboxColumn(width="small"),
                   "Quantità": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                   "€ per unità": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.0f €")},
    disabled=["Intervento", "Tipo", "Unità"],
)
ed["Costo"] = ed["Quantità"] * ed["€ per unità"]
sel = ed[ed["Scegli"]]
speso = sel["Costo"].sum()

st.header("3 · Il piano")
m1, m2, m3 = st.columns(3)
m1.metric("Budget", euro(budget))
m2.metric("Interventi scelti", euro(speso))
m3.metric("Restano" if budget >= speso else "Mancano", euro(abs(budget - speso)))
if budget:
    fig = go.Figure()
    colori = {"Rinnovabili e CER": "#2a78d6", "Efficienza energetica": "#eb6834", "Miglioramento ambientale": "#1baf7a", "Sensibilizzazione": "#eda100"}
    for tipo, g in sel.groupby("Tipo"):
        fig.add_trace(go.Bar(x=[g["Costo"].sum()], y=["Piano"], orientation="h", name=tipo, marker_color=colori[tipo],
                             marker_line=dict(color="white", width=2),
                             hovertemplate=f"{tipo}: %{{x:,.0f}} €<extra></extra>"))
    fig.add_vline(x=budget, line_color="#3b3a37", line_dash="dot", annotation_text="budget", annotation_position="top")
    fig.update_layout(barmode="stack", height=160, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(tickformat=",.0f"),
                      legend=dict(orientation="h", y=-0.4))
    st.plotly_chart(fig, use_container_width=True)
if budget and speso > budget:
    st.warning("Il piano supera il budget: riduci le quantità o cerca cofinanziamenti (vedi sotto).")

st.session_state["piano_interventi"] = [
    {"id": r["id"], "nome": r["Intervento"], "quantita": f"{r['Quantità']:g} {r['Unità']}", "costo": float(r["Costo"]),
     "q": float(r["Quantità"]), "cu": float(r["€ per unità"])} for _, r in sel.iterrows()]
if len(sel):
    st.page_link("pagine/convenzione.py", label="Inserisci questo piano nella bozza di convenzione", icon=":material/contract:")

st.header("4 · Le schede")
info = {x["id"]: x for x in CAT["interventi"]}
for _, r in sel.iterrows():
    x = info[r["id"]]
    with st.expander(f"{x['nome']} · {euro(r['Costo'])}"):
        st.markdown(f"**Beneficio**: {x['beneficio']}")
        st.markdown(f"**Costo indicativo**: {euro(x['intervallo'][0])}–{euro(x['intervallo'][1])} (unità: {x['unita']})")
        if x["leve"]:
            st.markdown("**Cofinanziamenti da verificare**: " + "; ".join(x["leve"]))
        if x["esempio"]:
            st.caption(x["esempio"])
