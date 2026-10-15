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

| Sezione | Pagina | Cosa fa |
|---|---|---|
| Per il Comune | Il mio progetto | Carica i documenti (PDF, Word) o inserisci i dati; stabilisce procedura, VIA e percentuali di legge |
| | Quanto vale | Scegli la percentuale e vedi il calcolo passo per passo; confronto con tutti i metodi |
| | Che iter è | Mappa interattiva del procedimento: fase attuale, scadenze, cosa fa il Comune |
| | La convenzione | Clausole da scegliere e bozza Word precompilata |
| | Come investirle | Piano degli interventi scelto dal catalogo, dentro il budget |
| | Fondo per i cittadini | Simulatore fondo perduto / fondo rotativo; regolamento e bando Word |
| Per le imprese | Sono un'impresa | Cosa succede se il Comune tace; proposta, sollecito, atto unilaterale d'obbligo (Word) |
| Per tutti | Catalogo delle misure | 110 misure con costi, beneficiari, ammissibilità; filtri ed export Excel |
| | Quadro FVG | Mappa e scheda per comune |
| | Casi FVG | Casi documentati |
| | Pavia di Udine | Analisi per singolo progetto (regole all'epoca, riferimento, margine, documenti), stima APE, rete |
| Per i cittadini | Perché servono | Prezzo dell'elettricità 2025 e quota di rinnovabili |

Il progetto inserito resta in memoria mentre si naviga tra le pagine e non viene salvato su server: con «Salva progetto» (barra laterale) si scarica un file .json da ricaricare in seguito.

## Struttura

```
compensazioni_FVG.py          navigazione
pagine/                   una pagina per file
core/compensazioni.py     calcoli (funzioni pure, testate)
core/iter.py              procedura e VIA secondo TU FER (schema semplificato)
core/estrazione.py        lettura dei documenti di progetto
core/convenzione_docx.py  bozza di convenzione Word
core/misure.py            database delle misure
core/fondo.py             simulazione fondo perduto e rotativo (+ fondo_docx.py)
core/pavia.py             analisi per progetto di Pavia di Udine
core/impresa_docx.py      modelli per l'impresa
core/dati.py              caricamento dati e formati italiani
data/regole/              percentuali, soglie, fasi dell'iter: ognuno con fonte e data
data/investimenti/        misure.csv: database delle misure (costi indicativi, ammissibilità)
data/prezzi/              prezzi orari 2025 e quota di rinnovabili
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
