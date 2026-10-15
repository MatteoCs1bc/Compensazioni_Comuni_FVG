import streamlit as st

from core.dati import euro
from core.misure import AMMISSIBILITA, FASCE, IMPEGNO, carica, excel, filtra

st.title("Catalogo delle misure")
st.markdown(
    "Tutte le misure che si possono finanziare con le compensazioni, dalle più piccole alle opere pubbliche, "
    "con costo indicativo, beneficiari, impegno per gli uffici e **grado di ammissibilità**. "
    "Le compensazioni devono rientrare in quattro categorie: miglioramento ambientale, efficienza energetica, "
    "fonti rinnovabili, sensibilizzazione (DM 10/9/2010, Allegato 2)."
)

d = carica()
benef = sorted({b for lista in d.beneficiari_lista for b in lista})
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    ambiti = c1.multiselect("Ambito", sorted(d.ambito.unique()))
    beneficiari = c2.multiselect("A chi va", benef)
    modalita = c3.multiselect("Come", sorted(m for m in d.modalita.unique() if m != "—"))
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1.4])
    fasce = c4.multiselect("Costo tipico", [f[2] for f in FASCE])
    impegno = c5.multiselect("Impegno per gli uffici", IMPEGNO)
    amm = c6.multiselect("Ammissibilità", AMMISSIBILITA, default=["Sicura", "Da verificare"])
    testo = c7.text_input("Cerca", placeholder="es. pompa di calore, siepi, scuola")

v = filtra(d, ambiti, beneficiari, modalita, fasce, impegno, amm, testo)
k = st.columns(4)
k[0].metric("Misure trovate", len(v))
k[1].metric("Ammissibilità sicura", int((v.ammissibilita == "Sicura").sum()))
k[2].metric("Da verificare", int((v.ammissibilita == "Da verificare").sum()))
k[3].metric("Sotto 10.000 €", int((v.fascia == FASCE[0][2]).sum()), help="Costo tipico = costo unitario × quantità tipica")

tab = v[["misura", "ambito", "categoria_dm2010", "beneficiari", "modalita", "costo_unitario", "unita",
         "costo_tipico", "impegno_uffici", "ammissibilita"]].rename(columns={
    "misura": "Misura", "ambito": "Ambito", "categoria_dm2010": "Categoria", "beneficiari": "A chi va",
    "modalita": "Come", "costo_unitario": "€ per unità", "unita": "Unità", "costo_tipico": "Costo tipico",
    "impegno_uffici": "Impegno uffici", "ammissibilita": "Ammissibilità"})
st.dataframe(tab, hide_index=True, use_container_width=True, height=430,
             column_config={"€ per unità": st.column_config.NumberColumn(format="%.0f €"),
                            "Costo tipico": st.column_config.NumberColumn(format="%.0f €")})

a, b, c = st.columns([1, 1, 2])
a.download_button("Scarica in Excel", excel(v), "misure_compensazione_fvg.xlsx", icon=":material/download:",
                  mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
b.download_button("Scarica in CSV", v.drop(columns=["beneficiari_lista"]).to_csv(index=False).encode("utf-8"),
                  "misure_compensazione_fvg.csv", mime="text/csv", icon=":material/download:")
c.page_link("pagine/investire.py", label="Componi il piano degli investimenti", icon=":material/savings:")

st.subheader("Scheda della misura")
if len(v):
    scelta = st.selectbox("Misura", v.misura.tolist(), label_visibility="collapsed")
    r = v[v.misura == scelta].iloc[0]
    colore = {"Sicura": "green", "Da verificare": "orange", "Esclusa": "red"}[r.ammissibilita]
    with st.container(border=True):
        st.markdown(f"### {r.misura}")
        st.markdown(f":{colore}-badge[{r.ammissibilita}] :blue-badge[{r.categoria_dm2010}] :gray-badge[{r.ambito}]")
        if r.descrizione:
            st.markdown(r.descrizione)
        x1, x2 = st.columns(2)
        if r.ammissibilita != "Esclusa":
            x1.markdown(f"**Costo indicativo**: {euro(r.costo_unitario_min)}–{euro(r.costo_unitario_max)} per {r.unita}  \n"
                        f"**Esempio**: {r.quantita_tipica:g} {r.unita} ≈ {euro(r.costo_tipico)} ({r.fascia})  \n"
                        f"**Impegno per gli uffici**: {r.impegno_uffici}")
            x2.markdown(f"**A chi va**: {r.beneficiari}  \n**Come**: {r.modalita}  \n"
                        + (f"**Come si misura**: {r.indicatore}" if r.indicatore else ""))
        st.markdown(f"**Ammissibilità**: {r.nota_ammissibilita}")
        if r.cofinanziamenti_e_cumulabilita:
            st.markdown(f"**Cofinanziamenti e cumulabilità**: {r.cofinanziamenti_e_cumulabilita}")
        if r.esempi_e_fonti:
            st.caption(f"Esempi e fonti: {r.esempi_e_fonti}")

st.caption(
    "Costi indicativi 2025–26, IVA esclusa, da sostituire con preventivi o prezziario regionale. «Da verificare» = "
    "ammissibile se motivata e scritta nella convenzione, ma esposta a contestazioni: chiedere conferma all'ufficio regionale "
    "o al segretario comunale. Le misure per imprese e agricoltori sono aiuti di Stato (regime de minimis). "
    "Fonti: DM 10/9/2010, All. 2; catalogo Città Metropolitana di Torino – Politecnico di Torino; stima APE FVG per "
    "Pavia di Udine (2026); casi FVG."
)
