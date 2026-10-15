import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compensazioni import ImpiantoProduzione, metodi_produzione, valore_scelto_bess
from core.dati import ROOT, comuni_indicatori, euro, nota_legale, num, pct, regole, tabella
from core.pavia import analisi, carica_analisi, excel_analisi, gruppi_zona

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

t0, t1, t2, t3, t4 = st.tabs(["Analisi per progetto", "Impianti e mappe", "Stima APE FVG", "Rete e territorio",
                              "Percorso partecipativo"])

with t0:
    an = analisi(fer, R)
    est = carica_analisi()
    st.markdown(
        "Ogni progetto dell'elenco comunale, **a prescindere dallo stato**: quale regola valeva quando è stato autorizzato, "
        "quanto valeva la compensazione di riferimento, cosa risulta prescritto, cosa può ancora fare il Comune e quali "
        "documenti mancano. Ordinati per priorità."
    )
    k = st.columns(4)
    k[0].metric("Progetti con margine alto", int((an.priorita == "Alta").sum()),
                help="In istruttoria, o autorizzati e non ancora realizzati con obbligo di compensazione")
    alti = an[an.priorita == "Alta"]
    k[1].metric("Riferimento al 3% sui progetti aperti", euro(alti.riferimento_3pct.sum()),
                help="Somma dei valori di riferimento al 3% dei proventi; per le batterie su ipotesi MACSE")
    k[2].metric("Progetti con compensazione nota", int(an.prescritta_eur.notna().sum()), help="Solo Cjase Sterpet: per gli altri servono i decreti integrali")
    k[3].metric("Progetti esterni all'elenco che toccano il Comune", len(est.get("esterni", [])))

    vista = an[["n", "impianto", "tipo", "mw", "stato", "regime", "regola_periodo", "obbligo", "riferimento_3pct",
                "prescritta_eur", "priorita", "margine"]].rename(columns={
        "n": "N.", "impianto": "Impianto", "tipo": "Tipo", "mw": "MW", "stato": "Stato", "regime": "Procedura",
        "regola_periodo": "Regole applicabili", "obbligo": "Obbligo di compensare", "riferimento_3pct": "Riferimento al 3%",
        "prescritta_eur": "Prescritta", "priorita": "Priorità", "margine": "Cosa può fare il Comune"})
    st.dataframe(vista, hide_index=True, use_container_width=True, height=420,
                 column_config={"Riferimento al 3%": st.column_config.NumberColumn(format="%.0f €"),
                                "Prescritta": st.column_config.NumberColumn(format="%.0f €"),
                                "MW": st.column_config.NumberColumn(format="%.2f")})
    st.download_button("Scarica l'analisi (Excel)", excel_analisi(an), "pavia_analisi_progetti.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/download:")

    st.subheader("Scheda del progetto")
    etich = {r.n: f"{r.n} · {r.impianto} ({num(r.mw, 2) + ' MW' if pd.notna(r.mw) else 'potenza n.d.'}) · {r.stato}"
             for r in an.itertuples()}
    scelto = st.selectbox("Progetto", list(etich), format_func=etich.get, label_visibility="collapsed")
    r = an[an.n == scelto].iloc[0]
    colore_p = {"Alta": "red", "Media": "orange", "Bassa": "gray", "—": "gray"}[r.priorita]
    with st.container(border=True):
        st.markdown(f"### {r.impianto}")
        st.markdown(f":{colore_p}-badge[Priorità {r.priorita.lower() if r.priorita != '—' else 'n.a.'}] "
                    f":blue-badge[{r.regime}] :gray-badge[{r.stato}]")
        b1, b2 = st.columns(2)
        with b1:
            st.markdown("**1 · Identità**")
            st.markdown(
                f"- Tipo e potenza: {r.tipo}, {num(r.mw, 3) + ' MW' if pd.notna(r.mw) else 'potenza non indicata'}\n"
                f"- Località: {r.localita or '—'} · zona: {r.zona or '—'}\n"
                f"- Superfici: complessiva {num(r.sup_complessiva_ha, 2)} ha, recintata {num(r.sup_recintata_ha, 2)} ha, "
                f"agricola con mitigazioni {num(r.sup_agricola_ha, 2)} ha\n"
                f"- Ente: {r.ente or '—'}\n- Titolo: {r.provvedimento or '—'}"
                + (f" ({r.data_nota})" if r.data_nota else "")
                + (f"\n- Proponente: {r.proponente}" if r.proponente else "")
                + (f"\n- Portale regionale: {r.portale}" if r.portale else "")
                + (f"\n- Bollettino: {r.bur}" if r.bur else ""))
            st.markdown("**2 · Regole applicabili**")
            st.markdown(f"*{r.regola_periodo}* · obbligo di compensare: **{r.obbligo}**  \n{r.regola_testo}")
        with b2:
            st.markdown("**3 · Compensazione**")
            if pd.notna(r.base_eur) and r.base_eur:
                righe_c = [f"- Base di calcolo: {r.base_testo}",
                           f"- Riferimento al 3% (metodo Agenzia FVG): **{euro(r.riferimento_3pct)}**"]
                if r.perc_max:
                    righe_c.append(f"- Intervallo per le regole del periodo ({pct(r.perc_min, 0)}–{pct(r.perc_max, 0)}): "
                                   f"{euro(r.minimo_legge)} – {euro(r.massimo_legge)}")
                st.markdown("\n".join(righe_c))
            else:
                st.markdown("- Valore di riferimento non calcolabile (potenza non indicata o tipo di impianto senza base).")
            if r.prescritta:
                st.markdown(f"- Prescritta: {r.prescritta}"
                            + (f" (valore {'stimato' if r.prescritta_stima else ''} {euro(r.prescritta_eur)})" if pd.notna(r.prescritta_eur) else ""))
                if pd.notna(r.rapporto):
                    st.markdown(f"- Corrisponde al **{pct(r.rapporto, 2)}** dei proventi stimati, contro il 3% di riferimento.")
            else:
                st.markdown("- Prescritta: **non nota** — serve il titolo integrale.")
            st.markdown("**4 · Territorio**")
            stessa = an[(an.zona == r.zona) & (an.n != r.n) & ~an.archiviato]
            st.markdown(f"- Nella stessa zona: {len(stessa)} {'altro progetto attivo' if len(stessa) == 1 else 'altri progetti attivi'}, "
                        f"{num(stessa.mw.sum(), 1)} MW"
                        + (f" ({', '.join(stessa.impianto.head(4))})" if len(stessa) else ""))
            st.markdown(f"- Rete: cabina primaria con inversione di flusso frequente ({int(rete.sezioni_invertite)} sezioni); "
                        f"{num(rete.mw_richiesti_sulle_aree, 0)} MW richiesti sull'area")
        st.markdown("**5 · Cosa può fare il Comune**")
        st.markdown(f"{r.margine}.")
        if r.priorita == "Alta":
            st.page_link("pagine/iter.py", label="Apri la mappa dell'iter per vedere i passaggi", icon=":material/route:")
        st.markdown("**6 · Documenti**")
        st.markdown("Da recuperare: " + "; ".join(est["documenti_comuni_mancanti"]) + ".")
        for nota in r.note:
            st.caption("• " + nota)

    if est.get("esterni"):
        st.subheader("Progetti che toccano il Comune ma non sono nell'elenco comunale")
        for x in est["esterni"]:
            with st.container(border=True):
                st.markdown(f"**{x['nome']}** · {x['proponente']} · {num(x['potenza_mw'], 2)} MW  \n"
                            f"{x['decreto']} · Comuni: {x['comuni']}  \n**Ruolo di Pavia di Udine**: {x['ruolo']}")
                st.caption(x["nota"])

    st.subheader("Cumulo per zona")
    gz = gruppi_zona(an)
    st.dataframe(gz.rename(columns={"zona": "Zona", "progetti": "Progetti attivi", "mw": "MW", "ha_agricoli": "Ettari agricoli"}),
                 hide_index=True, use_container_width=True,
                 column_config={"MW": st.column_config.NumberColumn(format="%.1f"),
                                "Ettari agricoli": st.column_config.NumberColumn(format="%.1f")})
    st.caption("Lettura giuridica semplificata: date dei titoli dall'elenco comunale, FAQ regionale sui procedimenti in corso, "
               "norme transitorie del TU FER. Da far confermare a un legale o agli uffici regionali prima dell'uso ufficiale.")

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
    rb, tot = [], {"capex": 0, "annuo": 0, "una": 0, "prov": 0}
    for nome, p, capex, ann, una in bess_ape:
        v4 = valore_scelto_bess(p, R, "bess_proventi")
        tot["prov"] += v4
        v1 = valore_scelto_bess(p, R, "bess_capex", capex_eur_mw=capex)
        v2 = valore_scelto_bess(p, R, "bess_annuo", eur_mw_anno=ann)
        v3 = valore_scelto_bess(p, R, "bess_una_tantum", eur_mw_una_tantum=una)
        tot["capex"] += v1; tot["annuo"] += v2; tot["una"] += v3
        rb.append({"Impianto": nome, "MW": p, "3% investimento": euro(v1), "€/MW/anno × 17,5 anni": euro(v2), "Una tantum €/MW": euro(v3),
                   "3% dei proventi × 15 anni": euro(v4)})
    rb.append({"Impianto": "Totale", "MW": 227.75, "3% investimento": euro(tot["capex"]),
               "€/MW/anno × 17,5 anni": euro(tot["annuo"]), "Una tantum €/MW": euro(tot["una"]),
               "3% dei proventi × 15 anni": euro(tot["prov"])})
    st.dataframe(pd.DataFrame(rb), hide_index=True, use_container_width=True)
    fig = go.Figure(go.Bar(x=[tot["capex"], tot["una"], tot["prov"], tot["annuo"]],
                           y=["3% dell'investimento", "Una tantum per MW", "3% dei proventi (legge FVG)", "Quota annua per MW"],
                           orientation="h", marker_color=["#9a9890", "#9a9890", "#2a78d6", "#9a9890"], width=0.45,
                           text=[euro(v) for v in (tot["capex"], tot["una"], tot["prov"], tot["annuo"])], textposition="outside",
                           hovertemplate="%{y}: %{x:,.0f} €<extra></extra>"))
    fig.update_layout(height=220, margin=dict(l=10, r=80, t=10, b=10), xaxis=dict(tickformat=",.0f", title="€ per i due accumuli"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Stessi due impianti (227,75 MW): da 5 a 15 milioni a seconda del metodo. In blu il metodo aggiunto dal tool, "
               "basato sulla legge regionale (3% dei proventi; ipotesi: 4 ore di durata e premio di capacità MACSE di "
               "13.000 €/MWh/anno per 15 anni). La scelta del metodo è il cuore della trattativa.")

    st.markdown("**Biometano** (esempio APE): 100 Smc/h × 8.000 h × 1,21 €/Smc × 15 anni × 3% = **435.600 €**.")

    st.info("L'analisi impianto per impianto, con le regole valide al momento dell'autorizzazione e il margine di "
            "trattativa, è nella scheda «Analisi per progetto».", icon=":material/arrow_back:")

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
