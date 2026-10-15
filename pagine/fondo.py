import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.dati import euro, num
from core.fondo import fondo_perduto, fondo_rotativo
from core.fondo_docx import documento
from core.misure import carica
from core.progetto import progetto

p = progetto()
salvato = p.get("fondo") or {}
BLU, ARANCIO = "#2a78d6", "#eb6834"


def k(nome, default):
    """Chiave di widget inizializzata dal progetto salvato."""
    chiave = f"fd_{nome}"
    if chiave not in st.session_state:
        st.session_state[chiave] = salvato.get(nome, default)
    return chiave


st.title("Fondo per i cittadini")
st.markdown(
    "Una parte delle compensazioni può tornare alle famiglie **sotto forma di interventi di efficienza in casa**: "
    "elettrodomestici efficienti, pompe di calore, piccolo fotovoltaico, isolamento. Il Comune crea un fondo a bilancio "
    "e ogni anno apre un bando. Due modelli: **contributi a fondo perduto** o **fondo rotativo** (prestiti a tasso zero "
    "che rientrano e finanziano altre famiglie)."
)

with st.expander("Prima di partire: le condizioni perché sia ammissibile", icon=":material/gavel:", expanded=False):
    st.markdown(
        "- **Scriverlo nella convenzione o nel decreto.** Le compensazioni non possono essere «meramente patrimoniali» "
        "(DM 10/9/2010, All. 2): la convenzione deve vincolare le somme a un *programma comunale di efficienza energetica "
        "per i cittadini*. Energia gratis o sconti in bolletta non passano (caso Udine San Gottardo).\n"
        "- **Bilancio.** Le somme entrano come entrata a destinazione vincolata; la ragioneria decide se la spesa è corrente "
        "o in conto capitale.\n"
        "- **Regolamento prima del bando.** Criteri e modalità vanno fissati prima, con un regolamento comunale "
        "(art. 12 della L. 241/1990).\n"
        "- **Fondo rotativo.** Il Comune non può prestare denaro direttamente ai cittadini: serve una convenzione con una "
        "banca o un confidi che istruisce, eroga e riscuote. In alternativa, contributo sugli interessi di un prestito bancario.\n"
        "- **Doppi finanziamenti.** Il bando deve dire se il contributo si somma o è alternativo a detrazioni, Conto Termico "
        "e bonus nazionali.\n\n"
        "Quadro generale, non parere legale: verificare con il Segretario comunale e il Responsabile finanziario."
    )

# ------------------------------------------------------------------ risorse
st.header("1 · Le risorse")
annua_calc = p.get("compensazione_annua_eur") or 0.0
c1, c2, c3 = st.columns(3)
cap = c1.number_input("Dotazione iniziale (€)", min_value=0.0, step=5000.0, key=k("capitale_iniziale", 0.0),
                      help="Per esempio una quota una tantum delle compensazioni.")
quota = c2.number_input("Quota annua (€)", min_value=0.0, step=1000.0, key=k("quota_annua", float(round(annua_calc * 0.5, -2)) or 20000.0),
                        help="Parte delle compensazioni annuali destinata al fondo." + (
                            f" Il calcolatore indica {euro(annua_calc)} all'anno di compensazione totale." if annua_calc else ""))
anni = c3.number_input("Anni", min_value=1, max_value=30, step=1, key=k("anni", 10))

# ------------------------------------------------------------------ modelli
st.header("2 · I due modelli a confronto")
a, b = st.columns(2)
with a.container(border=True):
    st.markdown("**Contributi a fondo perduto**")
    contributo = st.number_input("Contributo medio per famiglia (€)", min_value=50.0, step=50.0, key=k("contributo_medio", 400.0))
    gest_p = st.number_input("Costi di gestione (% del versato)", min_value=0.0, max_value=30.0, step=1.0,
                             key=k("gestione_perduto", 5.0)) / 100
with b.container(border=True):
    st.markdown("**Fondo rotativo (prestiti a tasso zero)**")
    prestito = st.number_input("Prestito medio per famiglia (€)", min_value=500.0, step=500.0, key=k("prestito_medio", 5000.0))
    r1, r2, r3 = st.columns(3)
    durata = r1.number_input("Anni di rimborso", min_value=1, max_value=15, step=1, key=k("durata_rimborso", 5))
    insolv = r2.number_input("Insolvenza (%)", min_value=0.0, max_value=50.0, step=1.0, key=k("insolvenza", 3.0)) / 100
    comm = r3.number_input("Commissione gestore (% annuo)", min_value=0.0, max_value=10.0, step=0.5, key=k("commissione", 1.0)) / 100

ep = fondo_perduto(cap, quota, int(anni), contributo, gest_p)
er = fondo_rotativo(cap, quota, int(anni), prestito, int(durata), insolv, comm)
tot_versato = cap + quota * anni
m = st.columns(4)
m[0].metric("Risorse versate", euro(tot_versato))
m[1].metric("Famiglie – fondo perduto", ep[-1].famiglie_cumulate, help=f"{euro(contributo)} ciascuna")
m[2].metric("Famiglie – fondo rotativo", er[-1].famiglie_cumulate, help=f"prestiti da {euro(prestito)}")
m[3].metric("Ancora nel fondo rotativo a fine periodo", euro(er[-1].cassa_fine + er[-1].credito_in_essere),
            help="Cassa più prestiti ancora da rimborsare: risorse che continuano a girare")

fig = go.Figure()
fig.add_trace(go.Scatter(x=[e.anno for e in ep], y=[e.famiglie_cumulate for e in ep], name="Fondo perduto",
                         mode="lines+markers", line=dict(color=ARANCIO, width=2)))
fig.add_trace(go.Scatter(x=[e.anno for e in er], y=[e.famiglie_cumulate for e in er], name="Fondo rotativo",
                         mode="lines+markers", line=dict(color=BLU, width=2)))
fig.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10), xaxis=dict(title="Anno", dtick=1),
                  yaxis=dict(title="Famiglie raggiunte (cumulate)", rangemode="tozero"),
                  legend=dict(orientation="h", y=1.12), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)
st.caption("Attenzione al confronto: il fondo perduto dà un aiuto piccolo a molte famiglie (adatto a elettrodomestici e "
           "piccoli interventi, e alle famiglie fragili); il rotativo anticipa somme più grandi che tornano indietro "
           "(adatto a pompe di calore, fotovoltaico, isolamento). Si possono usare insieme.")
with st.expander("Anno per anno"):
    st.dataframe(pd.DataFrame([{"Anno": x.anno, "Versato": euro(x.versato), "Contributi erogati": euro(x.erogato),
                                "Famiglie (perduto)": x.famiglie, "Prestiti erogati": euro(y.erogato), "Rientri": euro(y.rientri),
                                "Famiglie (rotativo)": y.famiglie, "Cassa rotativo": euro(y.cassa_fine)} for x, y in zip(ep, er)]),
                 hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ cosa finanzia
st.header("3 · Cosa finanzia il bando")
D = carica()
ammesse = D[D.modalita.isin(["Contributo con bando", "Fondo rotativo", "Fornitura in natura"])
            & D.beneficiari_lista.apply(lambda b: "Famiglie" in b or "Famiglie in povertà energetica" in b)
            & (D.ammissibilita != "Esclusa") & (D.id != "fondo_cittadini") & (D.id != "fondo_rotativo")]
default = [i for i in salvato.get("misure", ["elettrodomestici", "scaldacqua_pdc", "pdc_domestiche", "kit_efficienza"])
           if i in set(ammesse.id)]
k("misure", default)
scelte = st.multiselect("Interventi ammessi", ammesse.id.tolist(), key="fd_misure",
                        format_func=lambda i: ammesse.set_index("id").loc[i, "misura"])
mass = {}
if scelte:
    info = ammesse.set_index("id")
    salv_mass = salvato.get("massimali", {})
    df = pd.DataFrame([{"id": i, "Intervento": info.loc[i, "misura"], "Unità": info.loc[i, "unita"],
                        "Massimale (€)": float(salv_mass.get(i, info.loc[i, "costo_unitario_max"]))} for i in scelte])
    ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=["Intervento", "Unità"],
                        column_config={"id": None, "Massimale (€)": st.column_config.NumberColumn(min_value=0.0, step=50.0, format="%.0f €")},
                        key=f"fd_ed_{len(scelte)}_{'|'.join(scelte)[:60]}")
    mass = dict(zip(ed["id"], ed["Massimale (€)"]))

# ------------------------------------------------------------------ regolamento e bando
st.header("4 · Regolamento e bando")
g1, g2 = st.columns(2)
modello = g1.radio("Modello da usare nel regolamento", ["Fondo perduto", "Fondo rotativo"], horizontal=True,
                   key=k("modello", "Fondo perduto"))
nome = g2.text_input("Nome del fondo", key=k("nome", "Fondo comunale energia per i cittadini"))
h1, h2, h3, h4 = st.columns(4)
perc = h1.number_input("Contributo (% della spesa)", min_value=5, max_value=100, step=5, key=k("perc_contributo", 50))
tetto = h2.number_input("Tetto per famiglia all'anno (€)", min_value=0.0, step=100.0, key=k("tetto_famiglia", 2000.0))
isee = h3.number_input("Priorità con ISEE fino a (€)", min_value=0.0, step=1000.0, key=k("isee_priorita", 15000.0))
rottam = h4.toggle("Rottamazione obbligatoria", key=k("rottamazione", True))

stato = {"capitale_iniziale": cap, "quota_annua": quota, "anni": int(anni), "contributo_medio": contributo,
         "gestione_perduto": gest_p * 100, "prestito_medio": prestito, "durata_rimborso": int(durata),
         "insolvenza": insolv * 100, "commissione": comm * 100, "misure": scelte, "massimali": mass,
         "modello": modello, "nome": nome, "perc_contributo": perc, "tetto_famiglia": tetto, "isee_priorita": isee,
         "rottamazione": rottam}
p["fondo"] = stato
info = D.set_index("id")
doc = documento(p.get("comune") or "", "rotativo" if modello == "Fondo rotativo" else "perduto",
                dict(stato, prestito_max=prestito * 1.5),
                [{"misura": info.loc[i, "misura"], "unita": info.loc[i, "unita"], "massimale": mass.get(i)} for i in scelte])
d1, d2 = st.columns(2)
d1.download_button("Scarica regolamento e bando (.docx)", doc, f"regolamento_fondo_energia_{(p.get('comune') or 'comune').replace(' ', '_')}.docx",
                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary",
                   icon=":material/download:")


def nel_piano():
    piano = [x for x in st.session_state.get("piano_interventi", []) if x.get("id") != "fondo_cittadini"]
    piano.append({"id": "fondo_cittadini", "nome": "Fondo comunale energia per i cittadini (bandi annuali)",
                  "quantita": f"{int(anni)} anni", "costo": tot_versato, "q": float(anni),
                  "cu": tot_versato / anni if anni else 0.0})
    st.session_state["piano_interventi"] = piano
    st.session_state["piano_toccato"] = True
    st.session_state.pop("ms_misure", None)
    st.session_state["fd_msg"] = f"Fondo inserito nel piano: {euro(tot_versato)} in {int(anni)} anni."


d2.button("Inserisci il fondo nel piano degli investimenti", on_click=nel_piano, icon=":material/playlist_add:")
if st.session_state.get("fd_msg"):
    st.success(st.session_state.pop("fd_msg"))
    st.page_link("pagine/investire.py", label="Vai al piano", icon=":material/savings:")
st.caption(f"Con {euro(quota)} all'anno e un contributo medio di {euro(contributo)} si raggiungono circa "
           f"{num(quota * (1 - gest_p) / contributo, 0)} famiglie all'anno a fondo perduto.")
