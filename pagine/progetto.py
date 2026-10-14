import streamlit as st

from core.dati import comuni_indicatori
from core.estrazione import analizza, testo_da_file
from core.iter import AREE, NOMI_REGIME, TIPI, carica_iter
from core.progetto import aggiorna, esito, progetto

p = progetto()
COMUNI = [""] + sorted(comuni_indicatori().comune)
CAMPI = {"f_nome": "nome", "f_prop": "proponente", "f_comune": "comune", "f_tipo": "tipo",
         "f_mw": "potenza_mw", "f_bess": "bess_mw", "f_area": "area"}
for k, campo in CAMPI.items():
    st.session_state.setdefault(k, p[campo])
if p["compilato"] and not st.session_state.get("f_nome"):
    st.session_state["f_nome"] = p["nome"]

ESEMPI = {
    "Atlas Solar 1 (agrivoltaico, 13,3 MW, Bicinicco)": dict(f_nome="Agrivoltaico Atlas Solar 1", f_prop="Atlas Solar 1 S.r.l.",
        f_comune="Bicinicco", f_tipo="agrivoltaico", f_mw=13.336, f_bess=0.0, f_area="ordinaria"),
    "San Giovanni al Natisone 1+2 (FV, 5,7 MW)": dict(f_nome="San Giovanni al Natisone 1 e 2", f_prop="Chiron Energy SPV 50 S.r.l.",
        f_comune="San Giovanni Al Natisone", f_tipo="fv_terra", f_mw=5.696, f_bess=0.0, f_area="idonea"),
    "BESS Udine Sud (137,75 MW, Pavia di Udine)": dict(f_nome="BESS Udine Sud", f_prop="Aukera Italy 19 S.r.l.",
        f_comune="Pavia Di Udine", f_tipo="bess", f_mw=137.75, f_bess=0.0, f_area="ordinaria"),
}


def carica_esempio(nome):
    for k, v in ESEMPI[nome].items():
        st.session_state[k] = v


def usa_estratti():
    a = st.session_state.get("estratto") or {}
    if a.get("potenza_scelta"):
        st.session_state["f_mw"] = float(a["potenza_scelta"])
    if a.get("tipo"):
        st.session_state["f_tipo"] = a["tipo"]
    if a.get("comuni"):
        st.session_state["f_comune"] = a["comuni"][0]
    if a.get("proponente"):
        st.session_state["f_prop"] = a["proponente"]


st.title("Il mio progetto")
st.markdown(
    "Inserisci i dati del progetto che riguarda il tuo Comune: **carica i documenti** (relazione tecnica, istanza, "
    "decreto) e lo strumento prova a leggerli, oppure **compila le caselle a mano**. "
    "Da qui partono il calcolo delle compensazioni, la mappa dell'iter, la convenzione e il piano degli investimenti."
)

c1, c2 = st.columns([2, 1])
with c1:
    with st.container(border=True):
        st.markdown("**1 · Carica i documenti (facoltativo)**")
        files = st.file_uploader("PDF, Word o testo", type=["pdf", "docx", "txt"], accept_multiple_files=True,
                                 help="I file restano nella tua sessione e non vengono salvati.")
        if files and st.button("Leggi i documenti", icon=":material/search:"):
            testo = ""
            with st.spinner("Lettura in corso…"):
                for f in files:
                    try:
                        testo += "\n" + testo_da_file(f.name, f.getvalue())
                    except Exception as ex:  # file protetti o scansionati
                        st.warning(f"{f.name}: non riesco a leggerlo ({ex.__class__.__name__}). Se è una scansione, inserisci i dati a mano.")
                a = analizza(testo, [c for c in COMUNI if c])
            if a["caratteri"] < 200:
                st.warning("Ho trovato pochissimo testo: probabilmente il PDF è una scansione. Inserisci i dati a mano.")
            st.session_state["estratto"] = a
        a = st.session_state.get("estratto")
        if a:
            st.markdown("**Cosa ho trovato** – controlla e correggi")
            cand = sorted({v for v, _ in a["potenze_trovate"]}, reverse=True)
            if cand:
                default = cand.index(a["potenza_mw"]) if a["potenza_mw"] in cand else 0
                a["potenza_scelta"] = st.radio("Potenza dell'impianto (MW)", cand, index=default, horizontal=True,
                                               format_func=lambda v: f"{v:g}")
                with st.expander("Dove compaiono queste potenze"):
                    for v, ctx in a["potenze_trovate"]:
                        st.caption(f"**{v:g} MW** … {ctx[:220]} …")
            st.markdown(
                f"- Tipo: **{TIPI.get(a['tipo'], 'non riconosciuto')}**\n"
                f"- Comuni citati: **{', '.join(a['comuni']) or 'nessuno'}**\n"
                f"- Proponente: **{a['proponente'] or 'non trovato'}**\n"
                f"- Procedura citata: **{ {'au': 'autorizzazione unica', 'pas': 'PAS'}.get(a['procedura'], 'non indicata') }**"
                f"{' · cita la valutazione ambientale' if a['via'] else ''}"
            )
            st.button("Usa questi valori nella scheda", on_click=usa_estratti, type="primary")
with c2:
    with st.container(border=True):
        st.markdown("**Oppure parti da un esempio**")
        for nome in ESEMPI:
            st.button(nome, on_click=carica_esempio, args=(nome,), use_container_width=True)

with st.form("dati"):
    st.markdown("**2 · Dati del progetto**")
    a1, a2, a3 = st.columns(3)
    a1.text_input("Nome del progetto", key="f_nome")
    a2.text_input("Proponente", key="f_prop")
    a3.selectbox("Comune", COMUNI, key="f_comune")
    b1, b2, b3 = st.columns(3)
    b1.selectbox("Tipo di impianto", list(TIPI), format_func=TIPI.get, key="f_tipo")
    b2.number_input("Potenza (MW)", min_value=0.0, step=0.1, format="%.3f", key="f_mw")
    b3.number_input("Accumulo associato (MW, se c'è)", min_value=0.0, step=1.0, key="f_bess")
    st.radio("Dove si trova", list(AREE), format_func=AREE.get, key="f_area", horizontal=True)
    ok = st.form_submit_button("Salva e calcola", type="primary", icon=":material/check:")
if ok:
    dati = {campo: st.session_state[k] for k, campo in CAMPI.items()}
    if not dati["nome"]:
        dati["nome"] = f"Progetto {TIPI[dati['tipo']].lower()}" + (f" a {dati['comune']}" if dati["comune"] else "")
    aggiorna(**dati, compilato=True, compensazione_eur=None, compensazione_annua_eur=None, fase=None)
    st.rerun()

if p["compilato"]:
    e = esito()
    st.divider()
    st.subheader("Cosa vale per questo progetto")
    k1, k2, k3 = st.columns(3)
    for col, tit, val in [(k1, "Procedura", NOMI_REGIME[e.regime]),
                          (k2, "Valutazione ambientale", e.via.split("–")[0].strip()),
                          (k3, "Compensazione di legge", f"{e.perc_min:.0%}–{e.perc_max:.0%}" if e.perc_max else "nessun obbligo")]:
        with col.container(border=True):
            st.caption(tit)
            st.markdown(f"**{val}**")
    st.markdown(f"**Riferimento**: TU FER, {e.riferimento}  \n**Compensazioni**: {e.compensazione}  \n**Valutazione ambientale**: {e.via}")
    for n in e.note:
        st.caption("• " + n)
    st.caption("Schema semplificato del D.Lgs. 190/2024 (testo coordinato v7): da confermare con l'ufficio regionale competente.")
    s1, s2, s3, s4 = st.columns(4)
    s1.page_link("pagine/calcolatore.py", label="Calcola la compensazione", icon=":material/calculate:")
    s2.page_link("pagine/iter.py", label="Vedi l'iter", icon=":material/route:")
    s3.page_link("pagine/convenzione.py", label="Prepara la convenzione", icon=":material/contract:")
    s4.page_link("pagine/investire.py", label="Pianifica gli investimenti", icon=":material/savings:")
