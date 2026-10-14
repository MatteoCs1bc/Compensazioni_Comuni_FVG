import datetime as dt
import textwrap

import streamlit as st

from core.iter import AREE, NOMI_REGIME, TIPI, carica_iter
from core.progetto import aggiorna, checkbox, esito, progetto

p = progetto()
IT = carica_iter()

st.title("Che iter è: la mappa del procedimento")
if not p["compilato"]:
    st.info("Inserisci il progetto per avere la mappa giusta. Intanto puoi esplorare i tre percorsi.", icon=":material/info:")
    st.page_link("pagine/progetto.py", label="Vai a «Il mio progetto»", icon=":material/add_circle:")
    scelta = st.segmented_control("Percorso", ["Autorizzazione unica", "PAS", "Attività libera"], default="Autorizzazione unica")
    chiave = {"Autorizzazione unica": "au", "PAS": "pas", "Attività libera": "libera"}[scelta or "Autorizzazione unica"]
    con_via = True
else:
    e = esito()
    chiave = "au" if e.regime.startswith("au") else e.regime
    con_via = not e.via.startswith("Di norma nessuna")
    st.success(f"**{p['nome'] or 'Progetto'}** · {TIPI[p['tipo']]} · {p['potenza_mw']:g} MW · {AREE[p['area']]}  \n"
               f"Procedura: **{NOMI_REGIME[e.regime]}** (TU FER, {e.riferimento}) · {e.via}", icon=":material/route:")

fasi = [f for f in IT["fasi"][chiave] if con_via or not f.get("solo_se_via")]
ids = [f["id"] for f in fasi]
default = p["fase"] if p["fase"] in ids else ids[0]

st.markdown("**A che punto siamo?** Scegli la fase in cui si trova il progetto.")
fase = st.select_slider("Fase attuale", options=ids, value=default,
                        format_func=lambda i: next(f["titolo"] for f in fasi if f["id"] == i), label_visibility="collapsed")
aggiorna(fase=fase)
i_cur = ids.index(fase)


def nodo(i, f):
    giorni = f"\\n≤ {f['giorni']} giorni" if f.get("giorni") else ""
    etichetta = "\\n".join(textwrap.wrap(f["titolo"], 18)) + giorni
    if i < i_cur:
        stile = 'style="filled,rounded", fillcolor="#e8e7e3", color="#b5b3ac", fontcolor="#6b6a65"'
    elif i == i_cur:
        stile = 'style="filled,rounded,bold", fillcolor="#2a78d6", color="#2a78d6", fontcolor="white", penwidth=2'
    elif i == i_cur + 1:
        stile = 'style="rounded,bold", color="#2a78d6", fontcolor="#1d4f8c", penwidth=2'
    else:
        stile = 'style="rounded", color="#9a9890", fontcolor="#3b3a37"'
    tratteggio = ', style="rounded,dashed"' if f.get("opzionale") and i > i_cur else ""
    return f'n{i} [label="{etichetta}", shape=box, {stile}{tratteggio}, fontname="Helvetica", fontsize=11, margin="0.15,0.08"];'


per_riga = 5
dot = ["digraph G {", 'rankdir=TB; nodesep=0.35; ranksep=0.45; bgcolor="transparent";', 'edge [color="#9a9890", arrowsize=0.7];']
dot += [nodo(i, f) for i, f in enumerate(fasi)]
for r in range(0, len(fasi), per_riga):
    dot.append("{rank=same; " + " ".join(f"n{i}" for i in range(r, min(r + per_riga, len(fasi)))) + "}")
for i in range(len(fasi) - 1):
    stile = ' [color="#2a78d6", penwidth=2]' if i == i_cur else ""
    dot.append(f"n{i} -> n{i + 1}{stile};")
dot.append("}")
st.graphviz_chart("\n".join(dot), use_container_width=True)
st.caption("Grigio = fasi concluse · blu pieno = fase attuale · bordo blu = prossima fase · tratteggio = fase solo se necessaria. "
           "I giorni sono i termini massimi di legge.")

f = fasi[i_cur]
st.subheader(f"Fase attuale: {f['titolo']}")
c1, c2 = st.columns([3, 2])
with c1:
    st.markdown(f"{f['cosa']}")
    st.markdown(f"**Chi decide o agisce**: {f['chi']}")
    st.markdown("**Cosa può fare il Comune adesso**")
    for j, az in enumerate(f["comune"]):
        checkbox(az, f"az_{chiave}_{f['id']}_{j}")
with c2:
    with st.container(border=True):
        if f.get("giorni"):
            inizio = st.date_input("Questa fase è iniziata il", value=dt.date.today(), format="DD/MM/YYYY")
            scad = inizio + dt.timedelta(days=f["giorni"])
            st.metric("Scadenza massima", scad.strftime("%d/%m/%Y"), help=f"{f['giorni']} giorni dal {inizio.strftime('%d/%m/%Y')}")
            rest = (scad - dt.date.today()).days
            if 0 <= rest <= 15:
                st.warning(f"Mancano {rest} giorni.")
        else:
            st.caption("Per questa fase la legge non fissa un termine.")
        if f.get("documenti"):
            st.markdown("**Documenti da chiedere o controllare**")
            st.markdown("\n".join(f"- {d}" for d in f["documenti"]))
    if i_cur + 1 < len(fasi):
        nx = fasi[i_cur + 1]
        st.markdown(f"**Prossima fase**: {nx['titolo']}" + (f" (≤ {nx['giorni']} giorni)" if nx.get("giorni") else ""))
        st.caption(nx["cosa"])

with st.expander("Tutte le fasi in sequenza"):
    for i, x in enumerate(fasi):
        mark = "▶" if i == i_cur else ("✓" if i < i_cur else "·")
        st.markdown(f"**{mark} {x['titolo']}**" + (f" — ≤ {x['giorni']} giorni" if x.get("giorni") else "") + f"  \n{x['cosa']}")

st.caption("Fonti: D.Lgs. 190/2024 (TU FER, testo coordinato v7), artt. 7–9 e Allegati A–C; L.R. FVG 2/2025, art. 5; "
           "decreto MASE n. 441/2025 (moduli unici SUER); decreto AU n. 43585/GRFVG del 13/09/2024. "
           "Schema semplificato: per i casi particolari fare riferimento all'amministrazione procedente.")
