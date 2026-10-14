import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compensazioni import ImpiantoProduzione, metodi_bess, metodi_produzione, quota_ottenuta
from core.dati import euro, nota_legale, num, pct, regole

R = regole()
D = R["default_fvg"]
EVIDENZA, NEUTRO = "#2a78d6", "#9a9890"

ESEMPI = {
    "Nessun esempio": None,
    "Atlas Solar 1 – Bicinicco / S. Maria la Longa (13,3 MW, ottenuti 180.000 €)":
        dict(tipo="Agrivoltaico", mw=13.336, regime="Autorizzazione unica", ottenuto=180000.0),
    "Pavia di Udine – stima APE FVG, impianto FV 1 (6,37 MW)":
        dict(tipo="Fotovoltaico", mw=6.37, regime="Autorizzazione unica", ottenuto=0.0),
    "Pavia di Udine – BESS Udine Sud (137,75 MW)":
        dict(tipo="Solo accumulo (BESS)", mw=137.75, regime="Autorizzazione unica", ottenuto=0.0),
    "«Ci sarà un bel clima» – 10 pale da 6 MW":
        dict(tipo="Eolico", mw=60.0, regime="Autorizzazione unica", ottenuto=0.0),
}

st.title("Quanto vale: il calcolatore delle compensazioni")
st.markdown(
    "Mette **affiancati tutti i metodi** in uso. Il riferimento predefinito è il "
    "**metodo dell'Agenzia per l'Energia FVG**: 3% dei proventi annui stimati per gli anni di vita utile, "
    "senza attualizzazione. Gli altri metodi servono a capire dove si colloca una proposta."
)

es = st.selectbox("Parti da un esempio", list(ESEMPI))
e = ESEMPI[es] or {}
TIPI = ["Fotovoltaico", "Agrivoltaico", "Eolico", "Solo accumulo (BESS)", "Fotovoltaico + accumulo"]

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    tipo = c1.selectbox("Tipo di impianto", TIPI, index=TIPI.index(e.get("tipo", "Fotovoltaico")))
    regime = c2.radio("Procedura", ["PAS", "Autorizzazione unica"], horizontal=True,
                      index=1 if e.get("regime", "Autorizzazione unica") == "Autorizzazione unica" else 0,
                      help="PAS: fino a 1–3%. Autorizzazione unica: 1–4% (TU FER) e in FVG almeno 3% (L.R. 2/2025).")
    ottenuto = c3.number_input("Compensazione proposta o ottenuta (€, facoltativo)", min_value=0.0,
                               value=float(e.get("ottenuto", 0.0)), step=10000.0)

    produce = tipo != "Solo accumulo (BESS)"
    ha_bess = "accumulo" in tipo.lower() or "bess" in tipo.lower()

    if produce:
        st.markdown("**Impianto di produzione**")
        c1, c2, c3, c4 = st.columns(4)
        mw = c1.number_input("Potenza (MW)", min_value=0.0, value=float(e.get("mw", 10.0)) if produce else 10.0, step=0.5)
        chiave = "eolico" if tipo == "Eolico" else ("agrivoltaico" if tipo == "Agrivoltaico" else "fotovoltaico")
        ore = c2.number_input("Ore equivalenti (MWh/MW anno)", min_value=0, value=int(D["ore_equivalenti"][chiave]), step=50,
                              help="FV FVG: 1.337 h (PVGIS, stima APE per Pavia). Eolico: 2.000 h è il valore dell'esempio, da verificare sul sito.")
        prezzo = c3.number_input("Prezzo (€/MWh)", min_value=0.0, value=float(D["prezzo_eur_mwh"]), step=5.0,
                                 help="PUN medio 2025 usato da APE FVG.")
        vita = c4.number_input("Vita utile (anni)", min_value=1, value=int(D["vita_utile_anni"]), step=1)
        with st.expander("Opzioni avanzate"):
            a1, a2 = st.columns(2)
            sconto = a1.number_input("Tasso di attualizzazione (%)", min_value=0.0, value=0.0, step=0.5,
                                     help="0 = metodo APE. Il TU FER non specifica se il valore vada attualizzato.") / 100
            autoc = a2.number_input("Quota di autoconsumo (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0,
                                    help="Il TU FER calcola la base al netto dell'autoconsumo.") / 100

    if ha_bess:
        st.markdown("**Accumulo (BESS)**")
        b1, b2, b3, b4 = st.columns(4)
        mw_b = b1.number_input("Potenza accumulo (MW)", min_value=0.0,
                               value=float(e.get("mw", 50.0)) if not produce else 5.0, step=1.0)
        capex = b2.number_input("Investimento stimato (€/MW)", min_value=0, value=int(D["bess"]["capex_eur_mw"]), step=50000)
        vita_b = b3.number_input("Vita utile accumulo (anni)", min_value=1.0, value=float(D["bess"]["vita_utile_anni"]), step=0.5)
        coloc = b4.toggle("Co-locato con FV esistente", value=tipo == "Fotovoltaico + accumulo")

righe = []
if produce:
    imp = ImpiantoProduzione(mw, ore, prezzo, vita, sconto, autoc)
    risultati = metodi_produzione(imp, R)
    ag = risultati[0]
    st.subheader("Risultato")
    m1, m2, m3 = st.columns(3)
    m1.metric("Metodo Agenzia FVG – all'anno", euro(ag.annuo))
    m2.metric(f"Metodo Agenzia FVG – su {vita} anni", euro(ag.totale_min))
    m3.metric("Proventi stimati all'anno", euro(imp.proventi_anno),
              help=f"{num(imp.produzione_mwh_anno, 0)} MWh × {num(prezzo, 2)} €/MWh")
    if ottenuto:
        q = quota_ottenuta(ottenuto, imp)
        st.info(f"**{euro(ottenuto)}** corrispondono al **{pct(q['su_proventi_vita_senza_sconto'], 2)}** dei proventi "
                f"stimati su {vita} anni. Il metodo Agenzia indica il 3%; la legge regionale per l'autorizzazione unica "
                f"chiede almeno il 3%, il TU FER prevede 1–3% (PAS) o 1–4% (AU).")
    for r in risultati:
        rilevante = not ((r.metodo in ("tufer_au", "lr_fvg_au") and regime == "PAS") or (r.metodo == "tufer_pas" and regime != "PAS"))
        righe.append(dict(r=r, rilevante=rilevante))

if ha_bess:
    rb = metodi_bess(mw_b, R, capex_eur_mw=capex, vita_utile_anni=vita_b, colocato=coloc)
    st.subheader("Accumulo: tre metodi di prassi")
    st.caption("Per gli accumuli la legge non indica una base di calcolo: un BESS non vende energia prodotta. "
               "I tre approcci sono quelli proposti da APE FVG per Pavia di Udine e danno risultati molto diversi.")
    for r in rb:
        righe.append(dict(r=r, rilevante=True))

if righe:
    righe_v = [x for x in righe if x["rilevante"]]
    fig = go.Figure()
    nomi = [x["r"].nome for x in righe_v][::-1]
    for x in righe_v[::-1]:
        r = x["r"]
        col = EVIDENZA if r.metodo == "agenzia" else NEUTRO
        larg = max(r.totale_max - r.totale_min, 0)
        if larg == 0:
            fig.add_trace(go.Scatter(x=[r.totale_min], y=[r.nome], mode="markers",
                                     marker=dict(size=14, color=col, symbol="diamond"),
                                     hovertemplate=f"{r.nome}<br>{euro(r.totale_min)}<extra></extra>", showlegend=False))
        else:
            fig.add_trace(go.Bar(x=[larg], y=[r.nome], base=[r.totale_min], orientation="h", marker_color=col,
                                 width=0.45, hovertemplate=f"{r.nome}<br>{euro(r.totale_min)} – {euro(r.totale_max)}<extra></extra>",
                                 showlegend=False))
    if ottenuto and produce:
        fig.add_vline(x=ottenuto, line_dash="dot", line_color="#e34948",
                      annotation_text="ottenuto/proposto", annotation_position="top")
    fig.update_layout(height=70 + 55 * len(nomi), margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title="€ sull'intera vita utile", tickformat=",.0f", separatethousands=True),
                      yaxis=dict(categoryorder="array", categoryarray=nomi), bargap=0.4)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Barre = intervallo previsto dal metodo; rombo = valore unico. In blu il metodo predefinito.")

    tab = pd.DataFrame([{
        "Metodo": x["r"].nome,
        "Natura": {"legge": "Legge", "prassi": "Prassi", "proposta": "Proposta"}[x["r"].natura],
        "All'anno": euro(x["r"].annuo) if x["r"].annuo else "–",
        "Totale min": euro(x["r"].totale_min),
        "Totale max": euro(x["r"].totale_max),
        "Come si calcola": x["r"].nota,
        "Fonte": x["r"].fonte,
    } for x in righe_v])
    st.dataframe(tab, hide_index=True, use_container_width=True)

with st.expander("Cosa fa salire o scendere la cifra in trattativa"):
    f = R["fattori_negoziali"]
    a, b = st.columns(2)
    a.markdown("**Fanno salire**\n" + "\n".join(f"- {x}" for x in f["aumentano"]))
    b.markdown("**Fanno scendere**\n" + "\n".join(f"- {x}" for x in f["riducono"]))
    st.caption(f["fonte"])
with st.expander("Le compensazioni non sono soldi in cassa"):
    st.markdown(R["vincoli_dm_2010"]["testo"])
    st.caption(R["vincoli_dm_2010"]["fonte"])
st.caption(R["nota_vita_utile"])
nota_legale()
