"""Il progetto su cui si sta lavorando, condiviso tra tutte le pagine.

Il progetto vive nella sessione del browser. Con «Salva progetto» si scarica un file .json
che si può ricaricare in seguito con «Carica progetto salvato».
"""
import json
import re
from datetime import date

import streamlit as st

from core.iter import NOMI_REGIME, TIPI, determina_regime

VERSIONE_FILE = 1

DEFAULT = {
    "nome": "",
    "proponente": "",
    "comune": "",
    "tipo": "fv_terra",
    "potenza_mw": 10.0,
    "bess_mw": 0.0,
    "area": "non_so",
    "fase": None,
    "data_avvio": None,
    "ore": None,
    "prezzo": None,
    "vita": None,
    "percentuale": None,
    "compensazione_eur": None,
    "compensazione_annua_eur": None,
    "compilato": False,
}
# chiavi dei campi della pagina «Il mio progetto» ↔ campi del progetto
CAMPI_FORM = {"f_nome": "nome", "f_prop": "proponente", "f_comune": "comune", "f_tipo": "tipo",
              "f_mw": "potenza_mw", "f_bess": "bess_mw", "f_area": "area"}


def progetto() -> dict:
    if "progetto" not in st.session_state:
        st.session_state["progetto"] = dict(DEFAULT)
    return st.session_state["progetto"]


def aggiorna(**kw):
    p = progetto()
    p.update(kw)


def esito():
    p = progetto()
    return determina_regime(p["tipo"], p["potenza_mw"] or 0, p["area"])


# ------------------------------------------------------------------ spunte delle checklist
# Streamlit cancella lo stato dei widget quando si cambia pagina: le spunte vengono
# copiate in "_spunte" così sopravvivono alla navigazione e finiscono nel file salvato.

def checkbox(etichetta: str, key: str, default: bool = False, contenitore=None) -> bool:
    memo = st.session_state.setdefault("_spunte", {})
    if key not in st.session_state:
        st.session_state[key] = memo.get(key, default)
    v = (contenitore or st).checkbox(etichetta, key=key)
    memo[key] = v
    return v


# ------------------------------------------------------------------ salvataggio

def esporta() -> bytes:
    """Progetto, piano degli interventi e spunte delle checklist in un unico file JSON."""
    spunte = dict(st.session_state.get("_spunte", {}))
    dati = {
        "tipo_file": "compensazioni_fvg_progetto",
        "versione": VERSIONE_FILE,
        "salvato_il": date.today().isoformat(),
        "progetto": progetto(),
        "piano_interventi": st.session_state.get("piano_interventi", []),
        "spunte": spunte,
    }
    return json.dumps(dati, ensure_ascii=False, indent=2).encode("utf-8")


def importa(contenuto: bytes) -> str:
    """Ripristina un file salvato. Restituisce il nome del progetto caricato."""
    dati = json.loads(contenuto.decode("utf-8"))
    if dati.get("tipo_file") != "compensazioni_fvg_progetto":
        raise ValueError("Il file non è un progetto salvato da questo strumento.")
    p = dict(DEFAULT)
    p.update({k: v for k, v in dati.get("progetto", {}).items() if k in DEFAULT})
    if p["tipo"] not in TIPI:
        raise ValueError(f"Tipo di impianto sconosciuto: {p['tipo']}")
    st.session_state["progetto"] = p
    # campi del modulo: impostati qui, prima che la pagina crei i widget
    for k, campo in CAMPI_FORM.items():
        st.session_state[k] = p[campo]
    st.session_state["piano_interventi"] = dati.get("piano_interventi", [])
    st.session_state["piano_caricato"] = dati.get("piano_interventi", [])
    st.session_state["n_caricamenti"] = st.session_state.get("n_caricamenti", 0) + 1
    spunte = {k: v for k, v in dati.get("spunte", {}).items() if isinstance(v, bool)}
    st.session_state["_spunte"] = spunte
    for k, v in spunte.items():
        st.session_state[k] = v
    st.session_state.pop("estratto", None)
    return p["nome"] or "progetto"


def nome_file() -> str:
    p = progetto()
    base = p["nome"] or p["comune"] or "progetto"
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_")[:50] or "progetto"
    return f"{base}_{date.today().isoformat()}.json"


def _al_caricamento():
    f = st.session_state.get("carica_progetto")
    if f is None:
        return
    try:
        nome = importa(f.getvalue())
        st.session_state["msg_caricamento"] = ("ok", f"Caricato: {nome}")
    except Exception as ex:  # file sbagliato o danneggiato
        st.session_state["msg_caricamento"] = ("errore", f"Non riesco a caricare il file: {ex}")


# ------------------------------------------------------------------ barra laterale

def riepilogo_sidebar():
    p = progetto()
    with st.sidebar:
        st.divider()
        if p["compilato"]:
            e = esito()
            st.markdown(f"**{p['nome'] or 'Progetto senza nome'}**")
            st.caption(f"{TIPI[p['tipo']]} · {p['potenza_mw']:g} MW"
                       + (f" + BESS {p['bess_mw']:g} MW" if p["bess_mw"] else "")
                       + (f" · {p['comune']}" if p["comune"] else ""))
            st.caption(NOMI_REGIME[e.regime])
            if p.get("compensazione_eur"):
                v = f"{p['compensazione_eur']:,.0f} €".replace(",", ".")
                st.caption(f"Compensazione calcolata: {v}")
            st.page_link("pagine/progetto.py", label="Modifica il progetto", icon=":material/edit:")
            st.download_button("Salva progetto", data=esporta(), file_name=nome_file(), mime="application/json",
                               icon=":material/download:", use_container_width=True,
                               help="Scarica un file con progetto, calcolo, piano degli interventi e spunte. "
                                    "Ricaricalo qui sotto per riprendere il lavoro.")
        else:
            st.caption("Nessun progetto inserito.")
            st.page_link("pagine/progetto.py", label="Inserisci un progetto", icon=":material/add_circle:")
        with st.expander("Carica progetto salvato", icon=":material/upload:"):
            st.file_uploader("File .json salvato con questo strumento", type=["json"], key="carica_progetto",
                             on_change=_al_caricamento, label_visibility="collapsed")
            msg = st.session_state.pop("msg_caricamento", None)
            if msg:
                (st.success if msg[0] == "ok" else st.error)(msg[1])
