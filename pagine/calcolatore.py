import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compensazioni import ImpiantoProduzione, metodi_bess, metodi_produzione, proventi_bess
from core.dati import euro, nota_legale, num, pct, regole
from core.iter import TIPI
from core.progetto import aggiorna, esito, progetto

R = regole()
D = R["default_fvg"]
EVIDENZA, NEUTRO = "#2a78d6", "#9a9890"
p = progetto()

st.title("Quanto vale: il calcolatore")
if p["compilato"]:
    st.success(f"Stai lavorando su **{p['nome'] or 'progetto senza nome'}** · {TIPI[p['tipo']]} · {p['potenza_mw']:g} MW"
               + (f" · {p['comune']}" if p["comune"] else ""), icon=":material/folder_open:")
else:
    st.info("Nessun progetto inserito: puoi calcolare qui sotto oppure partire dalla pagina «Il mio progetto», "
            "che legge anche i documenti.", icon=":material/info:")
    st.page_link("pagine/progetto.py", label="Vai a «Il mio progetto»", icon=":material/add_circle:")

e = esito()
solo_bess = p["tipo"] == "bess"
mw_prod = 0.0 if solo_bess else float(p["potenza_mw"] or 0)
mw_bess = float(p["potenza_mw"] or 0) if solo_bess else float(p["bess_mw"] or 0)
chiave = "eolico" if p["tipo"] == "eolico" else ("agrivoltaico" if p["tipo"] == "agrivoltaico" else "fotovoltaico")

totale, annuo_tot = 0.0, 0.0
testo_calcolo = []

# ------------------------------------------------------------------ produzione
if not solo_bess:
    st.header("1 · I dati dell'impianto")
    c1, c2, c3, c4 = st.columns(4)
    mw = c1.number_input("Potenza (MW)", min_value=0.0, value=mw_prod or 10.0, step=0.5, format="%.3f")
    ore = c2.number_input("Ore di produzione all'anno", min_value=0, value=int(p["ore"] or D["ore_equivalenti"][chiave]), step=50,
                          help="MWh prodotti da 1 MW in un anno. FV in FVG: 1.337 (PVGIS, stima APE per Pavia). "
                               "Eolico: 2.000 è un valore di esempio, va verificato sul sito.")
    prezzo = c3.number_input("Prezzo dell'energia (€/MWh)", min_value=0.0, value=float(p["prezzo"] or D["prezzo_eur_mwh"]), step=5.0,
                             help="PUN medio 2025 usato da APE FVG: 116,07 €/MWh.")
    vita = c4.number_input("Anni di vita utile", min_value=1, value=int(p["vita"] or D["vita_utile_anni"]), step=1)
    with st.expander("Opzioni avanzate"):
        a1, a2 = st.columns(2)
        sconto = a1.number_input("Attualizzazione (% annuo)", min_value=0.0, value=0.0, step=0.5,
                                 help="0 = metodo Agenzia FVG. Con un tasso > 0 i ricavi futuri valgono meno di quelli di oggi.") / 100
        autoc = a2.number_input("Energia autoconsumata (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0,
                                help="Il TU FER calcola la base al netto dell'autoconsumo.") / 100
    imp = ImpiantoProduzione(mw, ore, prezzo, vita, sconto, autoc)

    st.header("2 · La percentuale")
    if e.perc_max:
        st.markdown(f"Per questo progetto la legge prevede **{pct(e.perc_min, 0)}–{pct(e.perc_max, 0)}** "
                    f"({'PAS' if e.regime == 'pas' else 'autorizzazione unica'}). Il metodo Agenzia FVG usa il **3%**.")
    else:
        st.markdown("Per questo progetto **non c'è un obbligo di legge**: la percentuale serve per proporre un accordo volontario.")
    perc = st.slider("Percentuale applicata", min_value=0.5, max_value=5.0, value=float(p["percentuale"] or 3.0), step=0.1,
                     format="%.1f%%") / 100
    if e.perc_max and not (e.perc_min - 1e-9 <= perc <= e.perc_max + 1e-9):
        st.warning(f"{pct(perc)} è fuori dall'intervallo di legge ({pct(e.perc_min, 0)}–{pct(e.perc_max, 0)}).")

    st.header("3 · Il calcolo, passo per passo")
    anni_eff = imp.fattore_anni()
    base_annua = imp.proventi_anno_netti
    righe = [
        ("Energia prodotta in un anno", f"{num(mw, 3)} MW × {num(ore, 0)} ore", f"{num(imp.produzione_mwh_anno, 0)} MWh"),
        ("Ricavi dalla vendita in un anno", f"{num(imp.produzione_mwh_anno, 0)} MWh × {num(prezzo, 2)} €/MWh", euro(imp.proventi_anno)),
    ]
    if autoc:
        righe.append(("Al netto dell'autoconsumo", f"{euro(imp.proventi_anno)} × (1 − {pct(autoc, 0)})", euro(base_annua)))
    annuo = base_annua * perc
    righe.append(("Compensazione all'anno", f"{euro(base_annua)} × {pct(perc)}", euro(annuo)))
    if sconto:
        righe.append(("Anni equivalenti, attualizzati", f"{vita} anni al {pct(sconto)}", num(anni_eff, 2)))
    tot_prod = annuo * anni_eff
    righe.append(("Compensazione sull'intera vita utile", f"{euro(annuo)} × {num(anni_eff, 2) if sconto else vita} anni", euro(tot_prod)))
    st.table(pd.DataFrame(righe, columns=["Passo", "Calcolo", "Risultato"]).set_index("Passo"))
    m1, m2 = st.columns(2)
    m1.metric("Compensazione all'anno", euro(annuo))
    m2.metric(f"Totale su {vita} anni", euro(tot_prod))
    totale += tot_prod
    annuo_tot += annuo
    aggiorna(potenza_mw=mw if p["compilato"] else p["potenza_mw"], ore=ore, prezzo=prezzo, vita=vita, percentuale=perc * 100)
    testo_calcolo.append("Impianto: " + "; ".join(f"{a}: {b} = {c}" for a, b, c in righe) + ".")

# ------------------------------------------------------------------ accumulo
bess_param = {}
if solo_bess or mw_bess:
    sb = p.get("bess") or {}

    def kb(nome, default):
        chiave = f"bs_{nome}"
        if chiave not in st.session_state:
            st.session_state[chiave] = sb.get(nome, default)
        return chiave

    DB = D["bess"]
    st.header("Accumulo (BESS)" if not solo_bess else "1 · L'accumulo")
    st.markdown(
        "Per gli accumuli la legge fissa la percentuale ma non una formula: un BESS non vende energia prodotta, però ha "
        "**proventi** (premio di capacità, arbitraggio, servizi alla rete). La legge regionale chiede **almeno il 3% dei "
        "proventi**: è il metodo predefinito. Gli altri tre sono metodi di prassi proposti dall'Agenzia FVG."
    )
    c1, c2 = st.columns([1, 2])
    mwb = c1.number_input("Potenza accumulo (MW)", min_value=0.0, value=mw_bess or 50.0, step=1.0)
    METODI_B = ["3% dei proventi (predefinito)", "Percentuale sull'investimento", "Quota annua per MW", "Una tantum per MW"]
    metodo = c2.radio("Metodo", METODI_B, horizontal=True, key=kb("metodo", METODI_B[0]))
    if metodo == METODI_B[0]:
        a, b, c, d_ = st.columns(4)
        ore_b = a.number_input("Durata (ore di scarica)", min_value=0.5, max_value=12.0, step=0.5, key=kb("durata_ore", float(DB["durata_ore"])),
                               help="MWh di capacità = MW × ore. Va presa dal progetto; 4 ore è un'ipotesi tipica.")
        prem = b.number_input("Premio di capacità (€/MWh all'anno)", min_value=0.0, step=500.0,
                              key=kb("premio", float(DB["premio_capacita_eur_mwh_anno"])),
                              help="Asta MACSE di Terna (30/09/2025): media ponderata circa 12.959 €/MWh/anno, per 15 anni. "
                                   "Metti 0 se l'impianto non ha un contratto di capacità.")
        altri = c.number_input("Altri ricavi (€/MW all'anno)", min_value=0.0, step=1000.0, key=kb("altri", float(DB["altri_ricavi_eur_mw_anno"])),
                               help="Arbitraggio e servizi di rete: chiedere il dato del business plan al proponente.")
        n_b = d_.number_input("Anni", min_value=1.0, step=1.0, key=kb("anni", float(DB["anni_proventi"])))
        pb = st.slider("Percentuale dei proventi", 1.0, 5.0, step=0.1, format="%.1f%%", key=kb("perc", 3.0)) / 100
        cap_mwh = mwb * ore_b
        prov = proventi_bess(mwb, ore_b, prem, altri)
        ann_b = prov * pb
        tot_b = ann_b * n_b
        passi = [("Capacità", f"{num(mwb, 2)} MW × {num(ore_b, 1)} ore", f"{num(cap_mwh, 0)} MWh"),
                 ("Premio di capacità all'anno", f"{num(cap_mwh, 0)} MWh × {euro(prem)}", euro(cap_mwh * prem))]
        if altri:
            passi.append(("Altri ricavi all'anno", f"{num(mwb, 2)} MW × {euro(altri)}", euro(mwb * altri)))
        passi += [("Proventi all'anno", "somma", euro(prov)),
                  ("Compensazione all'anno", f"{euro(prov)} × {pct(pb)}", euro(ann_b)),
                  ("Totale", f"{euro(ann_b)} × {num(n_b, 0)} anni", euro(tot_b))]
        if pb < 0.03:
            st.warning("Sotto il 3%: per le autorizzazioni uniche regionali sopra 1 MW la legge FVG chiede almeno il 3% dei proventi.")
        if not prem and not altri:
            st.warning("Senza premio di capacità né altri ricavi i proventi risultano zero: inserisci una stima.")
        bess_param = dict(durata_ore=ore_b, premio_eur_mwh_anno=prem, altri_ricavi_eur_mw_anno=altri, anni_proventi=n_b)
    elif metodo == METODI_B[1]:
        st.warning("Metodo senza base di legge: TU FER e legge regionale calcolano sui proventi, non sull'investimento. "
                   "Dà cifre molto più basse e una tantum.")
        a, b = st.columns(2)
        capex = a.number_input("Investimento stimato (€/MW)", min_value=0, step=50000, key=kb("capex", int(DB["capex_eur_mw"])))
        pb = b.slider("Percentuale", 1.0, 3.0, step=0.1, format="%.1f%%", key=kb("perc_capex", 3.0)) / 100
        inv = mwb * capex
        tot_b = inv * pb
        passi = [("Investimento", f"{num(mwb, 2)} MW × {euro(capex)}/MW", euro(inv)),
                 ("Compensazione una tantum", f"{euro(inv)} × {pct(pb)}", euro(tot_b))]
        ann_b = 0.0
    elif metodo == METODI_B[2]:
        a, b = st.columns(2)
        q = a.slider("€ per MW all'anno", 1000, 5000, step=250, key=kb("eur_mw_anno", 4000))
        vb = b.number_input("Anni", min_value=1.0, step=0.5, key=kb("anni_annuo", float(DB["vita_utile_anni"])))
        ann_b = mwb * q
        tot_b = ann_b * vb
        passi = [("Compensazione all'anno", f"{num(mwb, 2)} MW × {euro(q)}", euro(ann_b)),
                 ("Totale", f"{euro(ann_b)} × {num(vb, 1)} anni", euro(tot_b))]
    else:
        a, b = st.columns(2)
        coloc = a.toggle("Accanto a un impianto esistente (co-locato)", key=kb("colocato", False))
        lo, hi = (10000, 40000) if coloc else (20000, 60000)
        q = b.slider("€ per MW, una tantum", lo, hi, min(40000, hi), 1000)
        tot_b = mwb * q
        ann_b = 0.0
        passi = [("Compensazione una tantum", f"{num(mwb, 2)} MW × {euro(q)}", euro(tot_b))]
    st.table(pd.DataFrame(passi, columns=["Passo", "Calcolo", "Risultato"]).set_index("Passo"))
    st.metric("Compensazione accumulo", euro(tot_b))
    totale += tot_b
    annuo_tot += ann_b
    testo_calcolo.append(f"Accumulo ({metodo}): " + "; ".join(f"{a} = {c}" for a, b, c in passi[-2:]) + ".")
    p["bess"] = {**sb, **{k[3:]: v for k, v in st.session_state.items() if isinstance(k, str) and k.startswith("bs_")}}
    if solo_bess and p["compilato"]:
        aggiorna(potenza_mw=mwb)

aggiorna(compensazione_eur=totale, compensazione_annua_eur=annuo_tot, calcolo_testo=" ".join(testo_calcolo))

if not solo_bess and mw_bess:
    st.metric("Totale progetto (impianto + accumulo)", euro(totale))

# ------------------------------------------------------------------ confronto
st.header(f"{'2' if solo_bess else '4'} · Come si colloca: confronto e verifica")
ottenuto = st.number_input("Cifra proposta dal proponente o già ottenuta (€, facoltativo)", min_value=0.0, value=0.0, step=10000.0)
if ottenuto and totale:
    st.info(f"La cifra proposta è il **{pct(ottenuto / totale, 0)}** di quella calcolata qui ({euro(totale)}).")

voci = []
if not solo_bess:
    for r in metodi_produzione(imp, R):
        if (r.metodo in ("tufer_au", "lr_fvg_au") and e.regime == "pas") or (r.metodo == "tufer_pas" and e.regime not in ("pas",)):
            continue
        voci.append(r)
if solo_bess or mw_bess:
    voci += metodi_bess(mwb, R, **bess_param)
if voci:
    fig = go.Figure()
    nomi = [r.nome for r in voci][::-1]
    for r in voci[::-1]:
        col = EVIDENZA if r.metodo in ("agenzia", "bess_proventi") else NEUTRO
        larg = max(r.totale_max - r.totale_min, 0)
        if larg == 0:
            fig.add_trace(go.Scatter(x=[r.totale_min], y=[r.nome], mode="markers", marker=dict(size=14, color=col, symbol="diamond"),
                                     hovertemplate=f"{r.nome}<br>{euro(r.totale_min)}<extra></extra>", showlegend=False))
        else:
            fig.add_trace(go.Bar(x=[larg], y=[r.nome], base=[r.totale_min], orientation="h", marker_color=col, width=0.45,
                                 hovertemplate=f"{r.nome}<br>{euro(r.totale_min)} – {euro(r.totale_max)}<extra></extra>", showlegend=False))
    fig.add_vline(x=totale, line_color="#1baf7a", line_width=2, annotation_text="il tuo calcolo", annotation_position="top")
    if ottenuto:
        fig.add_vline(x=ottenuto, line_dash="dot", line_color="#e34948", annotation_text="proposta", annotation_position="bottom")
    fig.update_layout(height=90 + 55 * len(nomi), margin=dict(l=10, r=10, t=30, b=10),
                      xaxis=dict(title="€ sull'intera vita utile", tickformat=",.0f"),
                      yaxis=dict(categoryorder="array", categoryarray=nomi), bargap=0.4)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Barre = intervallo del metodo; rombo = valore unico (in blu il metodo predefinito). Linea verde = il tuo calcolo.")
    st.dataframe(pd.DataFrame([{"Metodo": r.nome, "Natura": r.natura, "Min": euro(r.totale_min), "Max": euro(r.totale_max),
                                "Come si calcola": r.nota, "Fonte": r.fonte} for r in voci]),
                 hide_index=True, use_container_width=True)

with st.expander("Cosa fa salire o scendere la cifra in trattativa"):
    f = R["fattori_negoziali"]
    a, b = st.columns(2)
    a.markdown("**Fanno salire**\n" + "\n".join(f"- {x}" for x in f["aumentano"]))
    b.markdown("**Fanno scendere**\n" + "\n".join(f"- {x}" for x in f["riducono"]))
st.caption(R["nota_vita_utile"])
nota_legale()
