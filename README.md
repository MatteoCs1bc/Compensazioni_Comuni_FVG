# Compensazioni FER · Friuli Venezia Giulia

Strumento per **Comuni** e **cittadini** sulle compensazioni dei grandi impianti rinnovabili
(fotovoltaico, agrivoltaico, eolico, accumuli) in Friuli Venezia Giulia.

## Avvio

```bash
pip install -r requirements.txt
streamlit run compensazioni_FVG.py
```

Pubblicazione: [Streamlit Community Cloud](https://streamlit.io/cloud) → *New app* → questo repository →
file principale `compensazioni_FVG.py`.

## Pagine

| Sezione | Pagina | Stato |
|---|---|---|
| Per il Comune | Quanto vale (calcolatore) | v0.1 |
| | Che iter è | in costruzione |
| | La convenzione | checklist; schema in arrivo |
| | Come investirle | in costruzione |
| Per tutti | Quadro FVG (mappa e scheda per comune) | v0.1 |
| | Casi FVG | v0.1 |
| | Pavia di Udine | v0.1 |
| Per i cittadini | Perché servono | in costruzione |

## Struttura

```
compensazioni_FVG.py          navigazione
pagine/                   una pagina per file
core/compensazioni.py     calcoli (funzioni pure, testate)
core/dati.py              caricamento dati e formati italiani
data/regole/              percentuali, soglie, parametri: ognuno con fonte e data
data/casi/                casi FVG documentati
data/territorio/          tabelle per comune (generate da scripts/build_territorio.py)
data/territorio/raw/      dati grezzi e README del pacchetto rete
data/pavia/               elenco FER del Comune di Pavia di Udine al 30/09/2026
tests/                    i test riproducono la stima APE FVG per Pavia di Udine
```

**Regola d'oro**: quando cambia una norma o un parametro si modifica `data/regole/compensazioni.yaml`,
non il codice.

## Metodi di calcolo

Predefinito: **metodo Agenzia per l'Energia FVG** (3% dei proventi annui stimati × anni di vita utile,
senza attualizzazione). Affiancati: TU FER (PAS 1–3%, AU 1–4%), L.R. FVG 2/2025 (AU ≥3%),
«Ci sarà un bel clima» (4% annuo) e, per gli accumuli, tre metodi di prassi (percentuale sull'investimento,
€/MW/anno, €/MW una tantum).

## Aggiornare i dati territoriali

```bash
pip install -r requirements-dev.txt
python scripts/build_territorio.py
pytest
```

## Fonti principali

D.Lgs. 190/2024 (TU FER, testo coordinato) · L.R. FVG 2/2025 (testo vigente dal 21/10/2025) ·
DM 10/9/2010 · APE FVG, stima compensazioni per Pavia di Udine (24/02/2026) · decreti AU pubblicati sul BUR FVG ·
portale regionale RIS_ENERG · aree delle cabine primarie e inversioni di flusso e-distribuzione.

Strumento informativo, non costituisce consulenza legale.
