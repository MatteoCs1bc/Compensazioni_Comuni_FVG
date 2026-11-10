import os
import zlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compensazioni import ImpiantoProduzione, metodi_produzione, valore_scelto_bess
from core.dati import ROOT, comuni_indicatori, euro, nota_legale, num, pct, regole, tabella
from core.pavia import (COLORI_STATO, analisi, carica_analisi, carica_scheda, excel_analisi, figura_mappa,
                        gruppi_zona, impianti_mappa, osm_pavia, scheda_docx, totali_scheda)
from core.suolo import (carica_suolo, confronto_vicini, consumo_fvg, conti, figura_affiancati, figura_annidati,
                        figura_pannelli, figura_rispetto_sau, figura_serie, figura_territorio, gruppi_tetto, gruppo_tetto_unico, quota_metano_colture, smc_prima,
                        impianti_df, ripartizione_territorio, rispetto_sau, serie_consumo, voci_consumi,
                        voci_panoramica)

R = regole()
D = R["default_fvg"]
fer = tabella("fer_pavia_al_2026-09-30.csv", cartella="pavia")
c = comuni_indicatori()
rete = c[c.comune == "Pavia Di Udine"].iloc[0]

MAPPA_STILE = os.environ.get("MAPPA_STILE_PAVIA", "open-street-map")  # "white-bg" se le tile non sono raggiungibili


def mappa_impianti(chiave: str):
    """Mappa OpenStreetMap con tutti gli impianti dell'elenco comunale, colorati per stato."""
    df = impianti_mappa()
    stati = st.pills("Stato degli impianti", list(COLORI_STATO), selection_mode="multi",
                     default=list(COLORI_STATO), key=f"{chiave}_stati")
    osm = st.toggle("Rete elettrica (linee, stazioni, cabine primarie e secondarie) e altri impianti (OpenStreetMap)", value=True, key=f"{chiave}_osm")
    st.plotly_chart(figura_mappa(df, stati or [], MAPPA_STILE, osm=osm_pavia() if osm else None), use_container_width=True, key=f"{chiave}_mappa",
                    config={"scrollZoom": True, "displaylogo": False})
    st.caption("Poligoni ricavati dalla cartografia Insiel del Comune «FER al 30-09-2026» (scala 1:20.000), numerati e "
               "descritti come nella tabella FER del Comune al 20/10/2026. La numerazione del Comune non usa 6, 9, 11, 14 e 15; "
               "il biogas (n. 10) compare solo nell'elenco al 30/09. Passa sopra il numero per i dati e la compensazione. Precisione di qualche metro: "
               "i tre accumuli coincidono con le coordinate del portale regionale. Linee, cabine, centrali e altri fotovoltaici: "
               "© OpenStreetMap contributors (ODbL), estrazione del 03/11/2026; su OSM mancano molti impianti recenti. "
               "Mappa di base © OpenStreetMap.")


SUOLO = carica_suolo()
CONSUMO = consumo_fvg()
cs = conti(SUOLO, CONSUMO[CONSUMO.comune == SUOLO["comune_ispra"]].iloc[0])


def sezione_suolo():
    """Suolo agricolo, consumo di suolo e superfici degli impianti, con i grafici a quadrati."""
    st.subheader("Suolo: quanto pesano gli impianti")
    st.markdown(
        f"Pavia di Udine ha **{num(cs['consumato_pct'], 1)}%** di suolo consumato, il doppio della media regionale "
        f"({num(CONSUMO[CONSUMO.pro_com == 0].iloc[0].consumato_2025_pct, 1)}%). Il tetto regionale del 3% della "
        f"superficie agricola vale circa **{num(cs['tetto'], 0)} ha**. Se è un tetto unico per fotovoltaico a terra, "
        f"accumuli e biometano, è **già superato**: gli impianti autorizzati in zona agricola occupano circa "
        f"**{num(cs['unico_aut'], 0)} ha**. Se vale per tipologia, il fotovoltaico (circa {num(cs['fv_aut'], 0)} ha) è a "
        "ridosso e gli accumuli sono sotto. Il testo non lo chiarisce: le due letture sono spiegate più sotto. "
        f"I tetti del comune adatti al fotovoltaico valgono **{num(cs['tetti_min'], 0)}–{num(cs['tetti_max'], 0)} ha**, "
        f"cioè circa {num(cs['tetti_mw_min'], 0)}–{num(cs['tetti_mw_max'], 0)} MW: quanto Cjase Sterpet."
    )
    k = st.columns(4)
    k[0].metric("Suolo consumato (2025)", f"{num(cs['consumato'], 0)} ha", f"+{num(cs['netto_2021_2025'], 1)} ha dal 2021",
                delta_color="inverse", help="ISPRA 2026. Comprende il fotovoltaico a terra, che ISPRA conta come consumo reversibile")
    k[1].metric("Superficie agricola (SAU)", f"{num(cs['sau'], 0)} ha",
                help="Censimento dell'agricoltura 2020: terreni delle aziende con centro aziendale a Pavia")
    k[2].metric("Tetto del 3% della SAU", f"{num(cs['tetto'], 0)} ha",
                f"{num(cs['unico_aut'], 0)} ha autorizzati (tetto unico)", delta_color="inverse",
                help=SUOLO["tetto"]["fonte_vigente"] + ": " + SUOLO["tetto"]["testo_vigente"].strip())
    k[3].metric("Tetti adatti al fotovoltaico", f"{num(cs['tetti_min'], 0)}–{num(cs['tetti_max'], 0)} ha",
                help=f"ISPRA 2026, superficie minima e massima; potenza stimata con {num(SUOLO['tetti_mw_per_ha'], 1)} MW per ettaro")

    vista = st.segmented_control("Visualizzazione", ["Uno dentro l'altro", "Affiancati"], default="Uno dentro l'altro",
                                 key="suolo_vista")
    if vista == "Affiancati":
        st.plotly_chart(figura_affiancati(voci_panoramica(cs)), use_container_width=True, key="suolo_aff",
                        config={"displayModeBar": False})
    else:
        st.plotly_chart(figura_annidati(voci_panoramica(cs, territorio=True)),
                        use_container_width=True, key="suolo_ann", config={"displayModeBar": False})
    st.caption("L'area di ogni quadrato è proporzionale agli ettari. Il tetto del 3% è tratteggiato perché è un limite, "
               "non una superficie occupata. Le colture per il biometano sono una stima dalla dieta dichiarata (dettagli nel riquadro qui sotto): "
               f"a Pavia ne sono coltivati solo {num(cs['mais_pavia'], 0)} ha, secondo il Comune, il resto è in altri comuni.")
    with st.expander("Come sono stimate le colture per il biometano"):
        m = SUOLO["mais_biometano"]
        st.markdown(
            f"- **A Pavia: {num(cs['mais_pavia'], 0)} ha** di colture energetiche per l'impianto ({m['fonte_pavia']}). "
            "Quasi tutta la biomassa arriva quindi da altri comuni: per Pavia l'impatto non è sul suolo agricolo ma sulla "
            "viabilità verso via Tombis (trasporto di biomasse e digestato) e su odori e digestato.\n"
            f"- **Piano di alimentazione dichiarato** (UdineToday): fino a **{num(m['colture_t'], 0)} t** di colture energetiche, "
            f"{num(m['effluenti_t'], 0)} t di effluenti zootecnici e {num(m['sottoprodotti_t'], 0)} t di sottoprodotti all'anno, "
            "da una quarantina di imprese.\n"
            f"- **Ettari**: {num(m['colture_t'], 0)} t diviso la resa degli insilati, {num(m['resa_t_ha_min'], 0)}–"
            f"{num(m['resa_t_ha_max'], 0)} t/ha → **{num(cs['mais_min'], 0)}–{num(cs['mais_max'], 0)} ha** "
            f"(valore centrale {num(cs['mais'], 0)} ha a {num(m['resa_t_ha'], 0)} t/ha, usato nei grafici).\n"
            f"- **Controllo sull'energia**: se fossero tutte mais insilato, le colture darebbero circa il "
            f"{num(quota_metano_colture(m) * 100, 0)}% dei {num(m['smc_anno'] / 1e6, 1)} milioni di Smc previsti; il resto "
            "viene da effluenti e sottoprodotti. I numeri sono coerenti.\n"
            f"- **Non è tutto suolo nuovo.** Dal 2012 c'era un biogas da {num(m['biogas_kwe_prima'], 0)} kWe, che consumava circa "
            f"{num(smc_prima(m) / 1e6, 1)} milioni di Smc di metano l'anno (ipotesi: rendimento elettrico del "
            f"{num(m['rendimento_elettrico'] * 100, 0)}%, {num(m['ore_prima'], 0)} ore). La riconversione circa raddoppia la "
            f"produzione: a parità di dieta la parte nuova è di **{num(cs['mais_min'] * cs['mais_quota_nuova'], 0)}–"
            f"{num(cs['mais_max'] * cs['mais_quota_nuova'], 0)} ha**.\n"
            "- Gli ettari reali possono essere meno: una parte delle colture può essere di secondo raccolto (dopo un'altra "
            "coltura sullo stesso campo) e una parte è fuori comune. Il dettaglio è nel **piano di approvvigionamento** "
            "allegato alla PAS del 14/01/2025.")

    t = SUOLO["tetto"]
    st.markdown("**Il tetto del 3% di suolo agricolo: due letture della norma**")
    st.markdown(f"> {t['testo_vigente'].strip()}\n>\n> — {t['fonte_vigente']}")
    with st.expander("Testo originale e definizione di superficie"):
        st.markdown(f"> {t['testo_originale'].strip()}\n>\n> — {t['fonte_originale']}\n\n"
                    "La L.R. 13/2025 ha aggiunto gli accumuli e tolto «le coperture delle»: conta la superficie "
                    f"dell'impianto, non solo quella coperta dai pannelli. {t['superficie'].strip()}")
    st.table(pd.DataFrame([
        {"Lettura": t["letture"][0]["nome"], "Argomento": t["letture"][0]["testo"].strip(),
         "Pavia oggi": f"{num(cs['unico_aut'], 0)} ha autorizzati su {num(cs['tetto'], 0)}: tetto già superato"},
        {"Lettura": t["letture"][1]["nome"], "Argomento": t["letture"][1]["testo"].strip(),
         "Pavia oggi": (f"FV {num(cs['fv_aut'], 0)} ha, accumuli {num(cs['bess_aut'], 0)} ha, biometano "
                        f"{num(cs['biometano'], 1)} ha, ciascuno su {num(cs['tetto'], 0)}")}]).set_index("Lettura"))
    st.warning(t["avvertenza"].strip())
    st.markdown("*Lettura A — tetto unico (quella che il Comune può sostenere)*")
    st.plotly_chart(figura_pannelli(gruppo_tetto_unico(cs)), use_container_width=True,
                    key="suolo_tetto_unico", config={"displayModeBar": False})
    st.markdown("*Lettura B — un tetto per tipologia*")
    st.plotly_chart(figura_pannelli(gruppi_tetto(cs)), use_container_width=True,
                    key="suolo_tetto", config={"displayModeBar": False})
    st.caption(
        "Contano solo gli impianti in zona agricola già autorizzati; in chiaro i progetti in istruttoria. "
        f"Esclusi Tombis (zona D2) e Lauzacco BESS (zona H2); Marconi ({num(cs['fv_incerta'], 1)} ha, zona S/E) è da "
        "verificare. Superficie complessiva (art. 5, c. 2), o recintata dove manca. Da chiarire con la Regione: se l'agrivoltaico conta "
        "come «moduli a terra» e se il tetto vale per i procedimenti avviati prima del 2025. La zona urbanistica di ogni "
        "impianto va confermata sul PRGC.")
    with st.expander("Impianti nel conto"):
        imp = impianti_df(SUOLO)
        st.dataframe(imp.rename(columns={"n": "N.", "nome": "Impianto", "tipologia": "Tipologia", "ha": "Ettari",
                                         "zona": "Zona", "gruppo": "Stato", "nota": "Nota"}).fillna(""),
                     hide_index=True, use_container_width=True)

    st.markdown("**Il territorio comunale: quanto è agricolo, quanto è consumato**")
    rip = ripartizione_territorio(cs, SUOLO)
    st.markdown(
        f"Su {num(cs['superficie'], 0)} ha di territorio, la SAU è il **{num(cs['sau'] / cs['superficie'] * 100, 1)}%** "
        f"e il suolo consumato il **{num(cs['consumato_pct'], 1)}%**. Dentro il suolo consumato gli impianti energetici già "
        f"realizzati sono circa {num(cs['realizzati'], 0)} ha: **{num(cs['realizzati_rev'], 0)} ha di fotovoltaico, consumo "
        f"reversibile** (in giallo), e **{num(cs['realizzati_perm'], 0)} ha di accumuli, stazione e biometano, consumo "
        "permanente** (in arancio). Il resto sono edifici, strade, piazzali e aree produttive, in prevalenza sigillati. "
        "Passa sopra un riquadro per la spiegazione, cliccalo per ingrandirlo.")
    st.plotly_chart(figura_territorio(rip), use_container_width=True, key="suolo_territorio",
                    config={"displayModeBar": False})
    st.caption("SAU dal censimento 2020, suolo consumato da ISPRA 2025: fonti diverse, la ripartizione è un ordine di "
               "grandezza. «Foraggere, orti, frutteti e altre colture»: tutto ciò che nel censimento non è cereali da granella, "
               "piante industriali, vite o prati; il mais da insilato sta qui. «Né agricolo né consumato»: corsi d'acqua e "
               "greti, boschi, incolti e terreni coltivati da aziende con sede in altri comuni, che il censimento non "
               "attribuisce a Pavia. Reversibile = suolo coperto ma non sigillato (fotovoltaico a terra, cantieri, sterrati); "
               "permanente = sigillato (edifici, strade asfaltate, platee, piazzali pavimentati). Per Pavia ISPRA non "
               "pubblica la ripartizione: quella degli impianti è nostra, sulla base del tipo di opera.")

    st.markdown("**Tutto in percentuale della SAU**")
    st.plotly_chart(figura_rispetto_sau(rispetto_sau(cs, SUOLO)), use_container_width=True, key="suolo_sau",
                    config={"displayModeBar": False})
    st.caption("Verde: colture; grigio: consumo di suolo ISPRA (anche se non tutto avviene su terreni agricoli); giallo: "
               "impianti; blu: i tetti, che non tolgono suolo agricolo. Le colture per il biometano sono quelle coltivate a Pavia "
               "secondo il Comune: non sono suolo consumato, ma terreno agricolo che cambia destinazione.")

    st.markdown("**Impianti e altri consumi di suolo**")
    st.plotly_chart(figura_affiancati(sorted(voci_consumi(cs), key=lambda v: -v["ha"]), lato_px=150, file_etichette=2),
                    use_container_width=True, key="suolo_consumi",
                    config={"displayModeBar": False})
    ctx = pd.DataFrame(SUOLO["contesto_2025"])
    fvg, ud = ctx.iloc[0], ctx.iloc[1]
    st.markdown(
        f"Dal 2006 il comune ha consumato **{num(cs['netto_2006_2025'], 0)} ha** in più. Gli impianti realizzati, con la "
        f"superficie complessiva dei progetti, sono {num(cs['realizzati_rev'], 0)} ha di fotovoltaico (**reversibile**: "
        f"tolto il fotovoltaico il suolo si può ripristinare) e {num(cs['realizzati_perm'], 0)} ha di accumuli, stazione e "
        f"biometano (**permanente**). EAGLE 1 aggiungerebbe {num(cs['bess_in_corso'], 0)} ha di consumo permanente; "
        f"Contessa {num(cs['fv_contessa'], 0)} ha di agrivoltaico, che ISPRA non conta come consumo. "
        f"Nel 2025 in FVG il consumo è stato per il **{num(100 * fvg.permanente_ha / fvg.consumo_ha, 0)}% permanente** e per "
        f"il {num(100 - 100 * fvg.permanente_ha / fvg.consumo_ha, 0)}% reversibile; i nuovi fotovoltaici a terra, tutti "
        f"reversibili, ne sono stati il **{num(fvg.fv_pct, 1)}%** (in provincia di Udine il {num(ud.fv_pct, 1)}%).")
    ctx = ctx.assign(reversibile_ha=ctx.consumo_ha - ctx.permanente_ha,
                     altro_rev_ha=ctx.consumo_ha - ctx.permanente_ha - ctx.fv_ha)[
        ["area", "consumo_ha", "permanente_ha", "reversibile_ha", "fv_ha", "altro_rev_ha", "fv_pct"]]
    nomi = {"area": "Area", "consumo_ha": "Consumo 2024–25 (ha)", "permanente_ha": "Permanente (ha)",
            "reversibile_ha": "Reversibile (ha)", "fv_ha": "di cui fotovoltaico a terra (ha)",
            "altro_rev_ha": "di cui cantieri, sterrati e altro (ha)", "fv_pct": "Fotovoltaico sul totale (%)"}
    st.dataframe(ctx.rename(columns=nomi), hide_index=True, use_container_width=True,
                 column_config={v: st.column_config.NumberColumn(format="%.1f") for k, v in nomi.items() if k != "area"})
    st.caption("ISPRA conta il fotovoltaico a terra ad alta densità come consumo di suolo reversibile; l'agrivoltaico "
               "e gli impianti a bassa densità sono «altre coperture», fuori dal conto. Per comune ISPRA non pubblica la "
               "ripartizione tra edifici, strade e impianti: solo per provincia e regione.")

    st.markdown("**Consumo di suolo nel tempo** (ISPRA, ettari netti all'anno)")
    st.plotly_chart(figura_serie(serie_consumo(CONSUMO[CONSUMO.comune == SUOLO["comune_ispra"]].iloc[0])),
                    use_container_width=True, key="suolo_serie", config={"displayModeBar": False})
    st.caption("I primi due periodi sono pluriennali (media annua). In rosso gli anni dei grandi impianti fotovoltaici. "
               "Per comune ISPRA dà solo il consumo totale, senza separare permanente e reversibile: negli anni in rosso il "
               "fotovoltaico (reversibile) pesa molto, come in tutta la provincia, dove nel 2025 il consumo è stato reversibile "
               "per il 94%.")

    st.markdown("**I comuni vicini**")
    v = confronto_vicini(CONSUMO, ["Pavia di Udine", "Santa Maria la Longa", "Pozzuolo del Friuli", "Pradamano",
                                   "Trivignano Udinese", "Udine"])
    st.dataframe(v.rename(columns={"comune": "Comune", "superficie_ha": "Superficie (ha)",
                                   "consumato_2025_ha": "Consumato 2025 (ha)", "consumato_2025_pct": "Consumato (%)",
                                   "netto_2021_2025": "Nuovo consumo 2021–25 (ha)", "netto_2024_2025": "di cui 2024–25 (ha)",
                                   "tetti_fv_min_ha": "Tetti FV min (ha)", "tetti_fv_max_ha": "Tetti FV max (ha)"}),
                 hide_index=True, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.1f") for c in
                                ["Superficie (ha)", "Consumato 2025 (ha)", "Consumato (%)", "Nuovo consumo 2021–25 (ha)",
                                 "di cui 2024–25 (ha)", "Tetti FV min (ha)", "Tetti FV max (ha)"]})
    st.caption("Santa Maria la Longa: +59 ha nel solo 2024–25, l'anno dei grandi fotovoltaici al confine con Pavia. "
               "Fonti: " + "; ".join(SUOLO["fonti"]) + ".")


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

ts, t0, t1, t2, t3, t4 = st.tabs(["Scheda compensazioni", "Analisi per progetto", "Impianti e mappe", "Stima APE FVG",
                                  "Rete e suolo", "Percorso partecipativo"])

with ts:
    s = carica_scheda()
    tot = totali_scheda(s)
    st.markdown(f"**{s['sintesi'].strip()}**")
    st.caption(f"Dai decreti e dalle schede FER forniti dal Comune · aggiornata al {s['aggiornato_al'].strftime('%d/%m/%Y')}")
    k = st.columns(4)
    k[0].metric("Compensazioni una tantum note", euro(tot["una_tantum_noto"]),
                help="Somma degli importi indicati nelle schede comunali e nei decreti; esclude le opere senza importo")
    k[1].metric("Sugli accumuli, per MW", f"{num(tot['bess_eur_mw_min'] / 1000, 0)}–{num(tot['bess_eur_mw_max'] / 1000, 0)} mila €",
                help="Enel 1,4 milioni su 200 MW; RNE14 1 milione su 90 MW. Una volta sola")
    k[2].metric("Impianti con quota annuale", tot["annuali"], help="Solo Crimea, per decisione della Regione in conferenza")
    k[3].metric("Progetti con priorità alta", tot["aperti"])
    st.download_button("Scarica la scheda da stampare (Word)", scheda_docx(s), "pavia_scheda_compensazioni.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", icon=":material/print:")

    st.subheader("Dove sono gli impianti")
    mappa_impianti("ts")

    st.subheader("Cosa emerge dai documenti")
    for x in s["novita"]:
        st.markdown(f"- **{x['titolo']}.** {x['testo'].strip()}")

    st.subheader("Compensazioni impianto per impianto")
    imp = s["impianti_df"].assign(valore=lambda d: d.eur_mw.map(lambda v: euro(v) if pd.notna(v) else None))
    imp.loc[imp.modalita == "annuale", "valore"] = "annuale"
    st.dataframe(imp[["n", "impianto", "mw", "titolo", "compensazione", "eur", "valore", "stato"]].rename(columns={
        "n": "N.", "impianto": "Impianto", "mw": "MW", "titolo": "Titolo", "compensazione": "Compensazione per Pavia",
        "eur": "Importo", "valore": "€ per MW", "stato": "Stato"}), hide_index=True, use_container_width=True,
        column_config={"MW": st.column_config.NumberColumn(format="%.2f"),
                       "Importo": st.column_config.NumberColumn(format="%.0f €")})
    for n in s.get("note_impianti", []):
        st.caption(n)

    st.subheader("Pavia e Santa Maria la Longa a confronto")
    st.markdown(s["confronto"]["testo"].strip())
    st.table(s["confronto_df"].rename(columns={"impianto": "Impianto", "pavia": "Pavia di Udine",
                                                "smll": "Santa Maria la Longa"}).set_index("Impianto"))

    st.subheader("Progetti da seguire adesso")
    st.markdown("Sui primi quattro l'importo è ancora aperto: è qui che conviene chiedere il modello Crimea, "
                "cioè il 3% annuo dei proventi.")
    st.dataframe(s["priorita_df"].rename(columns={"priorita": "Priorità", "n": "N.", "impianto": "Impianto",
                                                  "situazione": "Situazione", "azione": "Cosa fare"}),
                 hide_index=True, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Cosa pretendere nelle convenzioni")
        for x in s["clausole"]:
            st.checkbox(x, key=f"pv_cl_{zlib.crc32(x.encode())}")
        st.page_link("pagine/convenzione.py", label="Apri la bozza di convenzione", icon=":material/contract:")
    with c2:
        st.subheader("Documenti da recuperare")
        for x in s["documenti"]:
            st.checkbox(x, key=f"pv_doc_{zlib.crc32(x.encode())}")
    st.caption("Fonti: " + s["fonti"].strip())

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
    m0, m1, m2 = st.tabs(["Mappa interattiva", "Mappa del Comune", "Satellite"])
    with m0:
        mappa_impianti("t1")
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
        f"- Il limite regionale del **3% della superficie agricola** (L.R. 2/2025, art. 8, c. 3) vale circa "
        f"**{num(cs['tetto'], 0)} ha**. Riguarda fotovoltaico a terra, accumuli e biometano; il testo non chiarisce se il "
        f"tetto sia unico per le tre tipologie (a Pavia già superato: circa {num(cs['unico_aut'], 0)} ha) o uno per "
        "tipologia. Norma transitoria, in revisione. Il conto è nella sezione qui sotto."
    )
    st.markdown(
        "**Opposizione censita**: Comitato per la tutela del suolo agricolo (dal 2024), contro il consumo di suolo fertile "
        "per grandi impianti e l'impatto della nuova linea Terna. Area considerata «nodo strategico»."
    )
    sezione_suolo()

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
