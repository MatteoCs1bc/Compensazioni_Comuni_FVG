import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compensazioni import ImpiantoProduzione, metodi_produzione, valore_scelto_bess
from core.dati import ROOT, comuni_indicatori, euro, nota_legale, num, pct, regole, tabella

R = regole()
D = R["default_fvg"]
fer = tabella("fer_pavia_al_2026-09-30.csv", cartella="pavia")
c = comuni_indicatori()
rete = c[c.comune == "Pavia Di Udine"].iloc[0]

st.title("Pavia di Udine")
st.markdown(
    "Un comune di pianura di circa 35 km² attorno alla **stazione elettrica Terna «Udine Sud»**: "
    "qui si concentrano grandi impianti fotovoltaici e alcuni dei più grandi accumuli della regione. "
    "Dal luglio 2026 il Comune partecipa al progetto europeo **POWERUP** con l'Agenzia per l'Energia FVG."
)

attivi = fer[fer.stato != "Archiviata"]
bess = attivi[attivi.tipo == "BESS"]
fv = attivi[attivi.tipo == "FV"]
agri_ha = attivi.sup_agricola_mitigazione_ha.sum()
k = st.columns(4)
k[0].metric("Accumuli (BESS) nel comune", f"{num(bess.potenza_mw.sum(), 0)} MW",
            help="Realizzati, autorizzati e in istruttoria (elenco comunale al 30/09/2026)")
k[1].metric("Fotovoltaico", f"{num(fv.potenza_mw.sum(), 1)} MW", help="Realizzato, autorizzato o in corso; esclude le pratiche archiviate")
k[2].metric("Suolo agricolo occupato (con mitigazioni)", f"{num(agri_ha, 1)} ha",
            help="Somma della colonna «sup. impianto con mitigazione in zona agricola» dell'elenco comunale")
k[3].metric("MW richiesti sull'area di rete", num(rete.mw_richiesti_sulle_aree, 0),
            help="Area della cabina primaria principale, che si estende oltre il comune")

t1, t2, t3, t4 = st.tabs(["Impianti", "Compensazioni", "Rete e territorio", "Percorso partecipativo"])

with t1:
    st.markdown("Elenco del Comune al 30/09/2026 e cartografia regionale (Insiel) con la numerazione dell'elenco.")
    m1, m2 = st.tabs(["Mappa", "Satellite"])
    m1.image(str(ROOT / "assets" / "pavia_mappa_fer.jpg"), use_container_width=True)
    m2.image(str(ROOT / "assets" / "pavia_satellite_fer.jpg"), use_container_width=True)
    stato = st.multiselect("Stato", sorted(fer.stato.unique()), default=[s for s in fer.stato.unique() if s != "Archiviata"])
    vista = fer[fer.stato.isin(stato)].rename(columns={
        "n": "N.", "anno": "Anno", "tipo": "Tipo", "denominazione": "Impianto", "localizzazione": "Località",
        "potenza_mw": "MW", "sup_complessiva_ha": "Sup. complessiva (ha)", "sup_recintata_ha": "Sup. recintata (ha)",
        "sup_agricola_mitigazione_ha": "Sup. agricola con mitigazione (ha)", "ente": "Ente", "stato": "Stato",
        "provvedimento": "Provvedimento", "note": "Note"})
    st.dataframe(vista.astype(object).where(vista.notna(), ""), hide_index=True, use_container_width=True)
    agg = attivi[attivi.potenza_mw.notna()].groupby(["tipo", "stato"]).potenza_mw.sum().reset_index()
    st.dataframe(agg.rename(columns={"tipo": "Tipo", "stato": "Stato", "potenza_mw": "MW"}), hide_index=True)

with t2:
    st.subheader("La stima dell'Agenzia per l'Energia FVG (24/02/2026)")
    st.markdown(
        "Richiesta dal Comune il 2 febbraio 2026. Il tool riproduce esattamente i numeri della stima "
        "(verificato nei test automatici)."
    )
    ape_fv = [(1, 6.37, 8518.62466), (2, 4.98, 6659.7725), (3, 7.04, 9414.61815)]
    rows = []
    for n, p, prod in ape_fv:
        imp = ImpiantoProduzione(p, prod / p, D["prezzo_eur_mwh"], D["vita_utile_anni"])
        ag = metodi_produzione(imp, R)[0]
        rows.append({"Impianto FV": f"Impianto {n}", "MW": p, "MWh/anno": round(prod), "Proventi/anno": euro(imp.proventi_anno),
                     "3% all'anno": euro(ag.annuo, 2), f"Totale {D['vita_utile_anni']} anni": euro(ag.totale_min)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(R["nota_vita_utile"])

    st.markdown("**Accumuli: tre metodi, tre risultati**")
    bess_ape = [("BESS Udine Sud (Aukera)", 137.75, 700000, 4000, 40000), ("BESS Persereano (RNE 14)", 90, 800000, 3500, 30000)]
    rb, tot = [], {"capex": 0, "annuo": 0, "una": 0}
    for nome, p, capex, ann, una in bess_ape:
        v1 = valore_scelto_bess(p, R, "bess_capex", capex_eur_mw=capex)
        v2 = valore_scelto_bess(p, R, "bess_annuo", eur_mw_anno=ann)
        v3 = valore_scelto_bess(p, R, "bess_una_tantum", eur_mw_una_tantum=una)
        tot["capex"] += v1; tot["annuo"] += v2; tot["una"] += v3
        rb.append({"Impianto": nome, "MW": p, "3% investimento": euro(v1), "€/MW/anno × 17,5 anni": euro(v2), "Una tantum €/MW": euro(v3)})
    rb.append({"Impianto": "Totale", "MW": 227.75, "3% investimento": euro(tot["capex"]),
               "€/MW/anno × 17,5 anni": euro(tot["annuo"]), "Una tantum €/MW": euro(tot["una"])})
    st.dataframe(pd.DataFrame(rb), hide_index=True, use_container_width=True)
    fig = go.Figure(go.Bar(x=[tot["capex"], tot["una"], tot["annuo"]],
                           y=["3% dell'investimento", "Una tantum per MW", "Quota annua per MW"], orientation="h",
                           marker_color=["#9a9890", "#9a9890", "#2a78d6"], width=0.45,
                           text=[euro(v) for v in (tot["capex"], tot["una"], tot["annuo"])], textposition="outside",
                           hovertemplate="%{y}: %{x:,.0f} €<extra></extra>"))
    fig.update_layout(height=220, margin=dict(l=10, r=80, t=10, b=10), xaxis=dict(tickformat=",.0f", title="€ per i due accumuli"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Stessi due impianti (227,75 MW): da 5 a 15 milioni a seconda del metodo. La scelta del metodo è il cuore della trattativa.")

    st.markdown("**Biometano** (esempio APE): 100 Smc/h × 8.000 h × 1,21 €/Smc × 15 anni × 3% = **435.600 €**.")

    st.subheader("Cosa resta da negoziare")
    st.markdown(
        "Per gli impianti **realizzati** le compensazioni sono già fissate nei rispettivi decreti "
        "(per esempio, nell'autorizzazione di **Cjase Sterpet** è previsto un impianto da 400 kWp come compensazione). "
        "Lo spazio di trattativa riguarda le pratiche **in istruttoria** e quelle autorizzate per cui la convenzione "
        "non è ancora firmata."
    )
    aperte = attivi[attivi.stato.isin(["In corso", "Autorizzato"]) & attivi.potenza_mw.notna() & (attivi.potenza_mw >= 1)]
    rr = []
    for _, x in aperte.iterrows():
        if x.tipo == "BESS":
            lo = valore_scelto_bess(x.potenza_mw, R, "bess_una_tantum", eur_mw_una_tantum=20000)
            hi = valore_scelto_bess(x.potenza_mw, R, "bess_annuo")
            rif = valore_scelto_bess(x.potenza_mw, R, "bess_una_tantum")
            metodo = "BESS: una tantum 40.000 €/MW (intervallo: 20.000 €/MW una tantum – 4.000 €/MW/anno)"
        else:
            imp = ImpiantoProduzione(x.potenza_mw, D["ore_equivalenti"]["fotovoltaico"], D["prezzo_eur_mwh"], D["vita_utile_anni"])
            rif = metodi_produzione(imp, R)[0].totale_min
            lo, hi = imp.valore_vita_utile * 0.01, imp.valore_vita_utile * 0.04
            metodo = "FV: metodo Agenzia (intervallo TU FER 1–4%)"
        rr.append({"Impianto": x.denominazione, "Tipo": x.tipo, "MW": x.potenza_mw, "Stato": x.stato,
                   "Riferimento": euro(rif), "Minimo": euro(lo), "Massimo": euro(hi), "Metodo": metodo})
    st.dataframe(pd.DataFrame(rr), hide_index=True, use_container_width=True)
    st.caption("Valori indicativi calcolati con i parametri predefiniti del calcolatore; vanno verificati con i dati di progetto.")

with t3:
    a, b = st.columns(2)
    a.markdown(
        f"**Rete elettrica**\n"
        f"- Cabine primarie che servono il comune: **{int(rete.aree_cabina)}** (la principale ne copre il "
        f"{pct(rete.quota_area_principale, 0)})\n"
        f"- Progetti FER sulle aree di rete del comune: **{int(rete.progetti_sulle_aree)}**, "
        f"per **{num(rete.mw_richiesti_sulle_aree, 0)} MW** richiesti\n"
        f"- Inversione di flusso: **{int(rete.sezioni_invertite)}** sezioni, di cui {int(rete.sezioni_oltre_5pct)} "
        f"oltre il 5% del tempo → {rete.stato_indicativo.lower()}\n"
        f"- Comune diviso tra più cabine: **{'sì' if rete.comune_diviso else 'no'}**: una CER comunale non può coprire tutto il territorio"
    )
    km2 = rete.km2_comune
    b.markdown(
        f"**Suolo**\n"
        f"- Superficie comunale: **{num(km2, 1)} km²** ({num(km2 * 100, 0)} ha)\n"
        f"- Suolo agricolo occupato da impianti (con mitigazioni): **{num(agri_ha, 1)} ha**, pari al "
        f"**{pct(agri_ha / (km2 * 100), 1)} dell'intero territorio comunale**\n"
        f"- Il limite regionale del **3%** (L.R. 2/2025, art. 8 c. 3, ora esteso agli accumuli) si calcola sulla "
        f"**superficie agricola** del comune, non sul totale: serve il dato comunale di superficie agricola "
        f"per sapere quanto si è vicini al tetto."
    )
    st.markdown(
        "**Opposizione censita**: Comitato per la tutela del suolo agricolo (dal 2024), contro il consumo di suolo fertile "
        "per grandi impianti e l'impatto della nuova linea Terna. Area considerata «nodo strategico»."
    )

with t4:
    st.markdown(
        "**Accordo per l'adesione al progetto POWERUP** (Rep. n. 33/2026, firmato il 23/07/2026 tra il Comune e APE FVG). "
        "Il caso pilota si basa su **focus group locali** condotti da un facilitatore indipendente; dati anonimi; "
        "nessun costo per il Comune (fondi Horizon Europe). Il Comune indica un referente, aiuta a individuare e invitare "
        "gli stakeholder e mette a disposizione una sala."
    )
    st.markdown("**Struttura degli incontri** (concordata il 06/08/2026 tra Sindaco, Segretario, Assessore e APE FVG)")
    st.dataframe(pd.DataFrame({
        "Focus group": [1, 2, 3, 4, 5],
        "Partecipanti": ["Maggioranza consiliare", "Minoranza e consulta agricoltura e attività produttive",
                         "Giovani 20–35 anni", "Associazioni", "Cittadinanza"]}), hide_index=True)
    st.markdown(
        "**Intervista al Sindaco**: i temi della traccia che il tool può alimentare con dati\n"
        "- *D2 – perché qui*: terreni piani, prezzi dei terreni, vicinanza alla stazione Udine Sud → scheda Rete\n"
        "- *D12 – impatto cumulativo*: diversi impianti e un accumulo da 200 MW sulla stessa stazione, valutati uno per uno → "
        f"oggi **{num(bess.potenza_mw.sum(), 0)} MW** di accumuli nel solo comune\n"
        "- *D16 – compensazioni eque*: che cosa sarebbe un accordo equo → scheda Compensazioni\n"
        "- *D17 – CER e agrivoltaico* → il comune è diviso tra due cabine primarie"
    )
    st.markdown(
        "**Mappatura degli stakeholder**: il modello è pronto ma ancora vuoto. Categorie suggerite dalla traccia e "
        "dall'accordo: residenti, associazioni locali, proprietari terrieri, agricoltori e consulta agricoltura, "
        "attività produttive, Comitato per la tutela del suolo agricolo, sviluppatori (A2A / Volta Green Energy, "
        "Parco Solare Friulano 2, EcoEnergia Uno, Ilary Energia), Terna, comunità energetiche."
    )
nota_legale()
