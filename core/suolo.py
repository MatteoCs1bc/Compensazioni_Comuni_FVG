"""Suolo: superficie agricola, consumo di suolo (ISPRA) e superfici degli impianti.

Grafici «a quadrati»: l'area di ogni quadrato è proporzionale agli ettari, così si confrontano a colpo d'occhio
superfici molto diverse (centinaia di ettari agricoli contro pochi ettari di impianto).
- figura_affiancati: quadrati uno accanto all'altro, allineati in basso;
- figura_annidati: quadrati uno dentro l'altro, con lo stesso angolo in basso a sinistra; con più gruppi
  li mette affiancati alla stessa scala (es. il tetto del 3% per fotovoltaico, accumuli e biometano).
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
TESTO = "#1f2933"

COLORI = {"agricola": "#7cb02c", "territorio": "#dfe6d3", "consumato": "#808897", "mais": "#e04545",
          "fv": "#f7d038", "fv_chiaro": "#fbe9a0", "tetti": "#4f9bd9", "bess": "#e64a19", "bess_chiaro": "#f6b9a3",
          "biometano": "#6d8b2f", "tetto": "#1f2933"}


def _n(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ha(x: float) -> str:
    return _n(x, 0 if x >= 100 else 1) + " ha"


# --- dati -------------------------------------------------------------------------------------------------------

def carica_suolo() -> dict:
    return yaml.safe_load(open(ROOT / "data" / "pavia" / "suolo_pavia.yaml", encoding="utf-8"))


def consumo_fvg() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "territorio" / "consumo_suolo_fvg_2026.csv")


PERIODI = [("2006_2012", 6), ("2012_2015", 3), ("2015_2016", 1), ("2016_2017", 1), ("2017_2018", 1),
           ("2018_2019", 1), ("2019_2020", 1), ("2020_2021", 1), ("2021_2022", 1), ("2022_2023", 1),
           ("2023_2024", 1), ("2024_2025", 1)]


def serie_consumo(riga: pd.Series) -> pd.DataFrame:
    """Consumo di suolo netto per periodo, in ettari totali e in ettari all'anno."""
    return pd.DataFrame([{"periodo": p.replace("_", "–"), "anni": a, "ha": riga[f"netto_{p}"],
                          "ha_anno": riga[f"netto_{p}"] / a} for p, a in PERIODI])


def ettari_mais(m: dict, resa_t_ha: float | None = None) -> float:
    """Ettari di colture energetiche: tonnellate dichiarate nel piano di alimentazione / resa per ettaro."""
    return m["colture_t"] / (resa_t_ha or m["resa_t_ha"])


def quota_metano_colture(m: dict) -> float:
    """Controllo: quota del metano prodotto che le colture coprirebbero se fossero tutte mais insilato."""
    return min(1.0, m["colture_t"] * m["resa_ch4_nm3_t"] * m["nm3_smc"] / m["smc_anno"])


def smc_prima(m: dict) -> float:
    """Metano che consumava il vecchio cogeneratore a biogas, in Smc/anno: kWe / rendimento × ore / PCI."""
    return m["biogas_kwe_prima"] / m["rendimento_elettrico"] * m["ore_prima"] / m["pci_ch4_kwh_nm3"] * m["nm3_smc"]


def quota_nuova(m: dict) -> float:
    """Parte della produzione attuale che si aggiunge a quella del biogas del 2012."""
    return max(0.0, 1 - smc_prima(m) / m["smc_anno"])


def impianti_df(s: dict) -> pd.DataFrame:
    return pd.DataFrame(s["impianti"])


def conti(s: dict, consumo: pd.Series) -> dict:
    """Tutti i numeri della sezione suolo, calcolati dal file yaml e dalla riga ISPRA del comune."""
    imp = impianti_df(s)
    agr = imp[imp.zona == "agricola"]
    sau = s["agricoltura"]["sau_ha"]
    tetto = sau * s["tetto"]["quota"]

    def somma(df, tip, gruppi=("autorizzato",)):
        return float(df[(df.tipologia == tip) & df.gruppo.isin(gruppi)].ha.sum())

    m = s["mais_biometano"]
    real = imp[imp.get("realizzato", pd.Series(False, index=imp.index)).fillna(False).astype(bool)]
    return {
        "superficie": float(consumo.superficie_ha), "consumato": float(consumo.consumato_2025_ha),
        "consumato_pct": float(consumo.consumato_2025_pct), "sau": sau, "sat": s["agricoltura"]["sat_ha"],
        "tetto": tetto,
        "fv_aut": somma(agr, "fv"), "fv_incerta": somma(imp[imp.zona == "incerta"], "fv"),
        "fv_contessa": somma(agr, "fv", ("in_corso",)), "fv_tutti": float(imp[imp.tipologia == "fv"].ha.sum()),
        "bess_aut": somma(agr, "bess"), "bess_in_corso": somma(agr, "bess", ("in_corso",)),
        "bess_tutti": float(imp[imp.tipologia == "bess"].ha.sum()),
        "biometano": somma(agr, "biometano"),
        # tetto unico: fotovoltaico a terra + accumuli + biometano autorizzati in zona agricola (art. 8, c. 3, lettura A)
        "unico_aut": somma(agr, "fv") + somma(agr, "bess") + somma(agr, "biometano"),
        "unico_in_corso": somma(agr, "fv", ("in_corso",)) + somma(agr, "bess", ("in_corso",)),
        "mais": ettari_mais(m), "mais_min": ettari_mais(m, m["resa_t_ha_max"]),
        "mais_max": ettari_mais(m, m["resa_t_ha_min"]),
        "mais_quota_nuova": quota_nuova(m),
        "mais_pavia": float(m["colture_pavia_ha"]),
        "tetti_min": float(consumo.tetti_fv_min_ha), "tetti_max": float(consumo.tetti_fv_max_ha),
        "tetti_mw_min": float(consumo.tetti_fv_min_ha) * s["tetti_mw_per_ha"],
        "tetti_mw_max": float(consumo.tetti_fv_max_ha) * s["tetti_mw_per_ha"],
        "realizzati": float(real.ha.sum()),
        "realizzati_rev": float(real[real.consumo == "reversibile"].ha.sum()),
        "realizzati_perm": float(real[real.consumo == "permanente"].ha.sum()),
        "netto_2006_2025": float(sum(consumo[f"netto_{p}"] for p, _ in PERIODI)),
        "netto_2021_2025": float(sum(consumo[f"netto_{p}"] for p in ("2021_2022", "2022_2023", "2023_2024", "2024_2025"))),
    }


ALTRE_COLTURE = "Foraggere, orti, frutteti e altre colture"
RESTO = "Né agricolo né consumato"
MAIS_TILE = "Colture per il biometano"


def ripartizione_territorio(c: dict, s: dict, mais: bool = True) -> pd.DataFrame:
    """Territorio comunale diviso in SAU (per coltura), suolo consumato (reversibile/permanente dove si sa) e resto.
    SAU dal censimento 2020 e suolo consumato ISPRA 2025: fonti diverse, la somma è un ordine di grandezza.
    mais=True ricava dalla voce «foraggere e altre colture» (dove il censimento mette il mais da insilato) i 6 ha di
    colture energetiche che il Comune indica sul proprio territorio."""
    righe = [("Territorio comunale", "", c["superficie"])]
    righe.append(("Superficie agricola (SAU)", "Territorio comunale", c["sau"]))
    resto_sau = c["sau"]
    for col in s["colture"]:
        v = c["sau"] * col["pct"] / 100
        resto_sau -= v
        righe.append((col["nome"], "Superficie agricola (SAU)", v))
    if mais:
        m = min(c["mais_pavia"], resto_sau)
        resto_sau -= m
        righe.append((MAIS_TILE, "Superficie agricola (SAU)", m))
    righe.append((ALTRE_COLTURE, "Superficie agricola (SAU)", resto_sau))
    righe.append(("Suolo consumato", "Territorio comunale", c["consumato"]))
    righe.append(("Fotovoltaico a terra · reversibile", "Suolo consumato", c["realizzati_rev"]))
    righe.append(("Accumuli, stazione, biometano · permanente", "Suolo consumato", c["realizzati_perm"]))
    righe.append(("Edifici, strade, piazzali, aree produttive (in prevalenza permanente)", "Suolo consumato",
                  c["consumato"] - c["realizzati"]))
    righe.append((RESTO, "Territorio comunale", c["superficie"] - c["sau"] - c["consumato"]))
    return pd.DataFrame(righe, columns=["voce", "padre", "ha"])


def rispetto_sau(c: dict, s: dict) -> pd.DataFrame:
    """Ogni superficie in percentuale della SAU comunale, raggruppata per tipo."""
    sau = c["sau"]
    r = [(col["nome"], "Colture (censimento 2020)", sau * col["pct"] / 100) for col in s["colture"][:3]]
    r += [("Suolo consumato in totale (reversibile + permanente)", "Consumo di suolo (ISPRA)", c["consumato"]),
          ("Nuovo consumo 2006–2025", "Consumo di suolo (ISPRA)", c["netto_2006_2025"]),
          ("Nuovo consumo 2021–2025", "Consumo di suolo (ISPRA)", c["netto_2021_2025"]),
          ("Colture per il biometano a Pavia (dato del Comune)", "Colture energetiche", c["mais_pavia"]),
          ("FV + accumuli + biometano autorizzati (tetto unico)", "Impianti · tetto unico", c["unico_aut"]),
          ("Fotovoltaico a terra autorizzato · reversibile", "Impianti · consumo reversibile", c["fv_aut"]),
          ("Contessa, agrivoltaico · non conteggiato da ISPRA", "Impianti · non conteggiato", c["fv_contessa"]),
          ("Accumuli con EAGLE 1 · permanente", "Impianti · consumo permanente", c["bess_aut"] + c["bess_in_corso"]),
          ("Impianto di biometano · permanente", "Impianti · consumo permanente", c["biometano"]),
          ("Tetti adatti al fotovoltaico (max) · nessun consumo", "Alternative", c["tetti_max"])]
    df = pd.DataFrame(r, columns=["voce", "gruppo", "ha"])
    df["pct_sau"] = df.ha / sau * 100
    return df


def confronto_vicini(df: pd.DataFrame, comuni: list[str]) -> pd.DataFrame:
    v = df[df.comune.isin(comuni + ["Friuli-Venezia Giulia"])].copy()
    v["netto_2021_2025"] = v[["netto_2021_2022", "netto_2022_2023", "netto_2023_2024", "netto_2024_2025"]].sum(axis=1)
    v["ordine"] = v.comune.map(lambda c: (comuni + ["Friuli-Venezia Giulia"]).index(c))
    return v.sort_values("ordine")[["comune", "superficie_ha", "consumato_2025_ha", "consumato_2025_pct",
                                    "netto_2021_2025", "netto_2024_2025", "tetti_fv_min_ha", "tetti_fv_max_ha"]]


# --- grafici ----------------------------------------------------------------------------------------------------

def _voce(nome, valore, colore, contorno=False, nota="", testo=None, consumo=None):
    """Una superficie da disegnare. contorno=True: solo bordo tratteggiato (un limite, non un'occupazione).
    consumo: «reversibile», «permanente» o altro testo breve, scritto accanto agli ettari."""
    t = testo or ha(valore)
    if consumo:
        t += f" · {consumo}"
    return {"nome": nome, "ha": float(valore), "colore": colore, "contorno": contorno, "nota": nota, "testo": t}


def _etichetta(v):
    return f"<b>{v['nome']}</b><br>{v['testo']}"


def _hover(v):
    return f"<b>{v['nome']}</b><br>{v['testo']}" + (f"<br><i>{v['nota']}</i>" if v["nota"] else "")


def _quadrato(fig, x0, y0, lato, v, sfondo_contorno: bool = False):
    """sfondo_contorno=True: il quadrato tratteggiato ha il fondo bianco, così si vede anche con il tema scuro
    (solo dove non copre altri quadrati: grafici affiancati)."""
    import plotly.graph_objects as go
    x1, y1 = x0 + lato, y0 + lato
    if v["contorno"]:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=v["colore"], width=2, dash="dash"),
                      fillcolor="white" if sfondo_contorno else "rgba(0,0,0,0)",
                      layer="below" if sfondo_contorno else "above")
    else:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color="#4a5560", width=1),
                      fillcolor=v["colore"], layer="below")
    # punto invisibile per il passaggio del mouse
    fig.add_trace(go.Scatter(x=[x0 + lato / 2], y=[y0 + lato / 2], mode="markers",
                             marker=dict(size=max(8, min(40, lato * 6)), color="rgba(0,0,0,0)"),
                             hovertemplate=_hover(v) + "<extra></extra>", showlegend=False))


def _layout(fig, x0, x1, y0, y1, px):
    """Assi in unità «lato del quadrato più grande»; px = pixel per unità. L'altezza è calcolata perché la
    scala sia esatta (squadrati veri e distanze tra etichette in pixel) quando il contenitore è largo almeno
    (x1 - x0) * px; se è più stretto il grafico si rimpicciolisce in proporzione."""
    fig.update_xaxes(visible=False, range=[x0, x1], fixedrange=True)
    fig.update_yaxes(visible=False, range=[y0, y1], scaleanchor="x", scaleratio=1, fixedrange=True)
    fig.update_layout(height=round((y1 - y0) * px) + 10, margin=dict(l=0, r=0, t=5, b=5),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12), align="left"))
    fig.layout.meta = {"larghezza_px": round((x1 - x0) * px)}
    return fig


def _box(colore):
    colore = colore if colore != COLORI["territorio"] else "#9aa58a"
    return dict(bgcolor="white", bordercolor=colore, borderwidth=1.5, borderpad=4, font=dict(color=TESTO, size=12))


ETICHETTA_W, ETICHETTA_H = 200, 48  # ingombro di un'etichetta su due righe, in pixel (con margine)


def figura_affiancati(voci: list[dict], lato_px: int = 160, file_etichette: int = 3):
    """Quadrati affiancati, allineati in basso; etichette sotto, sfalsate su più file (come i quadrati FVG)."""
    import plotly.graph_objects as go
    fig = go.Figure()
    u = max(math.sqrt(v["ha"]) for v in voci)
    lati = [math.sqrt(v["ha"]) / u for v in voci]
    gap, minimo = 20 / lato_px, (ETICHETTA_W + 10) / file_etichette / lato_px
    centri, x = [], 0.0
    for i, lt in enumerate(lati):
        x = max(lt, ETICHETTA_W / lato_px) / 2 if i == 0 else max(x + (lati[i - 1] + lt) / 2 + gap, x + minimo)
        centri.append(x)
    for v, lt, cx in zip(voci, lati, centri):
        _quadrato(fig, cx - lt / 2, 0, lt, v, sfondo_contorno=True)
    riga = ETICHETTA_H / lato_px
    for i, (v, cx) in enumerate(zip(voci, centri)):
        fig.add_annotation(x=cx, y=-12 / lato_px - riga * (i % file_etichette), text=_etichetta(v), showarrow=False,
                           yanchor="top", align="center", **_box(v["colore"]))
    x1 = centri[-1] + max(lati[-1], ETICHETTA_W / lato_px) / 2 + 0.02
    return _layout(fig, -0.02, x1, -12 / lato_px - riga * file_etichette, 1.03, lato_px)


def figura_annidati(voci: list[dict], lato_px: int = 470):
    """Quadrati uno dentro l'altro con lo stesso angolo in basso a sinistra; etichette in colonna a destra,
    collegate all'angolo in alto a destra di ogni quadrato."""
    import plotly.graph_objects as go
    fig = go.Figure()
    voci = sorted(voci, key=lambda v: -v["ha"])
    u = math.sqrt(voci[0]["ha"])
    lati = [math.sqrt(v["ha"]) / u for v in voci]
    for v, lt in zip(voci, lati):
        if not v["contorno"]:
            _quadrato(fig, 0, 0, lt, v)
    for v, lt in zip(voci, lati):
        if v["contorno"]:
            _quadrato(fig, 0, 0, lt, v)
    passo = ETICHETTA_H / lato_px
    top, fondo = 1.0 - passo / 2 + 0.02, passo / 2
    ys = []
    for lt in lati:
        y = min(lt, top) if not ys else min(lt, ys[-1] - passo)
        ys.append(y)
    if ys[-1] < fondo:  # troppe etichette in basso: si risale mantenendo il passo
        ys[-1] = fondo
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = max(ys[i], ys[i + 1] + passo)
    xl = 1.0 + 40 / lato_px
    gomito = 1.0 + 12 / lato_px
    for v, lt, y in zip(voci, lati, ys):
        # linea a gomito: orizzontale sul lato alto del quadrato fino al margine, poi all'etichetta. Le linee
        # orizzontali stanno a quote diverse e i tratti obliqui sono nello stesso ordine: non si incrociano.
        fig.add_shape(type="path", path=f"M {lt},{lt} L {gomito},{lt} L {xl},{y}",
                      line=dict(color="#39424e", width=1.2))
        fig.add_trace(go.Scatter(x=[lt], y=[lt], mode="markers", hoverinfo="skip", showlegend=False,
                                 marker=dict(size=6, color="white", line=dict(color="#39424e", width=1.5))))
        fig.add_annotation(x=xl, y=y, text=_etichetta(v), showarrow=False, xanchor="left", yanchor="middle",
                           align="left", **_box(v["colore"]))
    return _layout(fig, -0.01, xl + ETICHETTA_W / lato_px, -0.01, max(1.0, ys[0] + passo / 2) + 0.01, lato_px)


def figura_pannelli(gruppi: list[tuple[str, list[dict]]], lato_px: int = 150):
    """Più gruppi di quadrati annidati, affiancati alla stessa scala; etichette in elenco sotto ogni pannello."""
    import plotly.graph_objects as go
    fig = go.Figure()
    u = max(math.sqrt(v["ha"]) for _, vv in gruppi for v in vv)
    larg = max(1.0, (ETICHETTA_W + 30) / lato_px) + 40 / lato_px
    riga, titolo_h = ETICHETTA_H / lato_px, 52 / lato_px
    n_max = max(len(vv) for _, vv in gruppi)
    for j, (titolo, voci) in enumerate(gruppi):
        x0 = j * larg
        # cartoncino bianco dietro ogni pannello: tratteggi e titoli leggibili anche con il tema scuro
        fig.add_shape(type="rect", x0=x0 - 8 / lato_px, y0=-12 / lato_px - n_max * riga, x1=x0 + larg - 22 / lato_px,
                      y1=1.0 + titolo_h - 2 / lato_px, fillcolor="white", line=dict(color="#d5dae0", width=1), layer="below")
        voci = sorted(voci, key=lambda v: -v["ha"])
        for v in voci:
            if not v["contorno"]:
                _quadrato(fig, x0, 0, math.sqrt(v["ha"]) / u, v)
        for v in voci:
            if v["contorno"]:
                _quadrato(fig, x0, 0, math.sqrt(v["ha"]) / u, v)
        fig.add_annotation(x=x0, y=1.0 + 6 / lato_px, text=f"<b>{titolo}</b>", showarrow=False, xanchor="left",
                           yanchor="bottom", align="left", font=dict(color=TESTO, size=13), bgcolor="white")
        for i, v in enumerate(voci):
            fig.add_annotation(x=x0, y=-12 / lato_px - i * riga, text=_etichetta(v), showarrow=False, xanchor="left",
                               yanchor="top", align="left", **_box(v["colore"]))
    return _layout(fig, -0.01, len(gruppi) * larg, -12 / lato_px - n_max * riga, 1.0 + titolo_h, lato_px)


def figura_serie(serie: pd.DataFrame, evidenzia_da: str = "2021–2022"):
    """Consumo di suolo netto in ettari all'anno (i primi due periodi sono pluriennali: media annua)."""
    import plotly.graph_objects as go
    i0 = list(serie.periodo).index(evidenzia_da)
    colori = ["#9aa3ad" if i < i0 else "#e04545" for i in range(len(serie))]
    fig = go.Figure(go.Bar(x=serie.periodo, y=serie.ha_anno, marker_color=colori,
                           text=[_n(v, 1) for v in serie.ha_anno], textposition="outside",
                           customdata=serie[["ha", "anni"]],
                           hovertemplate="%{x}: %{customdata[0]:.2f} ha in %{customdata[1]} anni"
                                         "<br>%{y:.2f} ha all'anno<extra></extra>"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="ettari all'anno",
                      showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
    fig.update_yaxes(range=[0, max(serie.ha_anno) * 1.2])
    return fig


COLORI_GRUPPO = {"Colture (censimento 2020)": COLORI["agricola"], "Consumo di suolo (ISPRA)": COLORI["consumato"],
                 "Colture energetiche": COLORI["mais"], "Impianti · consumo reversibile": COLORI["fv"],
                 "Impianti · non conteggiato": COLORI["fv_chiaro"], "Impianti · tetto unico": "#c98a1a", "Impianti · consumo permanente": COLORI["bess"],
                 "Alternative": COLORI["tetti"]}


def figura_territorio(df: pd.DataFrame):
    """Il territorio comunale come un quadrato diviso in parti proporzionali agli ettari (treemap)."""
    import plotly.graph_objects as go
    col = {"Territorio comunale": "#f4f6f1", "Superficie agricola (SAU)": COLORI["agricola"], "Cereali": "#9cc45a",
           "Piante industriali (soprattutto soia)": "#b5d47e", "Vite": "#6f9a2e", "Prati permanenti e pascoli": "#c9e0a0",
           ALTRE_COLTURE: "#d8e8bd", MAIS_TILE: "#f2b8b8", "Suolo consumato": COLORI["consumato"],
           "Fotovoltaico a terra · reversibile": COLORI["fv"], "Accumuli, stazione, biometano · permanente": COLORI["bess"],
           "Edifici, strade, piazzali, aree produttive (in prevalenza permanente)": "#a7adb6", RESTO: COLORI["territorio"]}
    spiega = {
        ALTRE_COLTURE: "Censimento 2020: foraggere avvicendate (anche il mais da insilato), ortive, frutteti, legumi, terreni a riposo",
        MAIS_TILE: "6 ha a Pavia, dato del Comune (10/11/2026); in tutto l'impianto ne usa circa 510–680, quasi tutti in altri comuni",
        RESTO: "Corsi d'acqua e greti, boschi, incolti, terreni coltivati da aziende con sede in altri comuni",
        "Fotovoltaico a terra · reversibile": "Pannelli su suolo non sigillato: ISPRA lo conta come consumo reversibile",
        "Accumuli, stazione, biometano · permanente": "Platee, fondazioni, vasche, piazzali: suolo in prevalenza sigillato",
        "Edifici, strade, piazzali, aree produttive (in prevalenza permanente)":
            "Per singolo comune ISPRA non separa permanente e reversibile: qui ci sono anche cantieri, sterrati e cave",
    }
    breve = {ALTRE_COLTURE: "Foraggere, orti,<br>frutteti e altro", MAIS_TILE: "Colture per<br>il biometano",
             "Piante industriali (soprattutto soia)": "Piante industriali<br>(soprattutto soia)",
             "Prati permanenti e pascoli": "Prati", RESTO: "Né agricolo<br>né consumato",
             "Fotovoltaico a terra · reversibile": "Fotovoltaico<br>reversibile",
             "Accumuli, stazione, biometano · permanente": "Accumuli, stazione,<br>biometano · permanente",
             "Edifici, strade, piazzali, aree produttive (in prevalenza permanente)":
                 "Edifici, strade, piazzali,<br>aree produttive (in prevalenza permanente)"}
    tot = df.loc[df.voce == "Territorio comunale", "ha"].iloc[0]
    testo = [f"{ha(v)} · {_n(v / tot * 100, 1)}% del territorio" for v in df.ha]
    nota = [spiega.get(v, "") for v in df.voce]
    vis = [f"<b>{breve.get(v, v)}</b><br>{t}" for v, t in zip(df.voce, testo)]
    pattern = [dict(shape="/", fgcolor="#e98b8b", size=10, solidity=0.15) if v == MAIS_TILE else dict(shape="")
               for v in df.voce]
    fig = go.Figure(go.Treemap(labels=df.voce, parents=df.padre, values=df.ha, branchvalues="total",
                               marker=dict(colors=[col.get(v, "#ccc") for v in df.voce], line=dict(color="white", width=2),
                                           pattern=dict(shape=[p["shape"] for p in pattern],
                                                        fgcolor=[p.get("fgcolor", "#000") for p in pattern],
                                                        size=10, solidity=0.15)),
                               text=vis, customdata=list(zip(testo, nota)), texttemplate="%{text}",
                               textfont=dict(color=TESTO, size=13),
                               hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>%{percentParent:.1%} di «%{parent}»"
                                             "<br><i>%{customdata[1]}</i><extra></extra>",
                               tiling=dict(pad=3), pathbar=dict(visible=False), maxdepth=3, sort=True))
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      uniformtext=dict(minsize=9, mode="hide"),
                      hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12), align="left"))
    return fig


def figura_rispetto_sau(df: pd.DataFrame, tetto_pct: float = 3.0):
    """Barre orizzontali: ogni superficie in percentuale della SAU; linea tratteggiata sul tetto del 3%."""
    import plotly.graph_objects as go
    d = df.iloc[::-1]
    xmax = max(d.pct_sau) * 1.45
    fig = go.Figure(go.Bar(x=d.pct_sau, y=d.voce, orientation="h", marker_color=[COLORI_GRUPPO[g] for g in d.gruppo],
                           textposition="none", customdata=d.gruppo,
                           hovertemplate="<b>%{y}</b><br>%{x:.1f}% della SAU<br>%{customdata}<extra></extra>"))
    # valori in una colonna a destra, lontani dalla linea del tetto
    fig.add_trace(go.Scatter(x=[max(d.pct_sau) * 1.08] * len(d), y=d.voce, mode="text", textposition="middle right",
                             text=[f"<b>{_n(p, 1)}%</b> · {ha(h)}" for p, h in zip(d.pct_sau, d.ha)],
                             textfont=dict(color="#6b7480", size=12), hoverinfo="skip", showlegend=False))
    fig.add_vline(x=tetto_pct, line=dict(color=COLORI["tetto"], width=1.5, dash="dash"), layer="below",
                  annotation_text="tetto 3%", annotation_position="top", annotation_font_color=TESTO)
    fig.update_layout(height=40 * len(d) + 60, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title="% della SAU comunale",
                      hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12)))
    fig.update_xaxes(range=[0, xmax], ticksuffix="%", tickvals=[0, 3, 10, 20, 30])
    return fig


def voci_consumi(c: dict) -> list[dict]:
    """Il suolo consumato del comune e, dentro, il nuovo consumo e gli impianti (realizzati e in progetto)."""
    return [
        _voce("Suolo consumato al 2025", c["consumato"], COLORI["consumato"], consumo="perm. + rev.", nota="ISPRA 2026: edifici, strade, aree produttive, impianti"),
        _voce("Nuovo consumo 2006–2025", c["netto_2006_2025"], "#5d6570", nota="Netto: al netto dei ripristini"),
        _voce("Fotovoltaico realizzato", c["realizzati_rev"], COLORI["fv"], consumo="reversibile",
              nota="Cjase Sterpet, Risano, San Mauro e Selvuzzis; superficie complessiva dei progetti"),
        _voce("Accumuli, stazione, biometano", c["realizzati_perm"], COLORI["bess"], consumo="permanente",
              nota="BESS Enel, sottostazione Santo Stefano, biometano; in prevalenza sigillato"),
        _voce("Nuovo consumo 2021–2025", c["netto_2021_2025"], COLORI["mais"], nota="Gli anni dei grandi fotovoltaici"),
        _voce("EAGLE 1 (in istruttoria)", c["bess_in_corso"], COLORI["bess_chiaro"], consumo="permanente",
              nota="Accumulo: se autorizzato, suolo in prevalenza sigillato"),
        _voce("Contessa (in istruttoria)", c["fv_contessa"], COLORI["fv_chiaro"], consumo="agrivoltaico",
              nota="Agrivoltaico a bassa densità: ISPRA non lo conta come consumo, ma occupa il suolo agricolo"),
    ]


# --- composizioni per la scheda di Pavia -----------------------------------------------------------------------

def voci_panoramica(c: dict, territorio: bool = False) -> list[dict]:
    v = []
    if territorio:
        v.append(_voce("Territorio comunale", c["superficie"], COLORI["territorio"], nota="ISPRA 2026"))
    v += [
        _voce("Superficie agricola (SAU)", c["sau"], COLORI["agricola"], nota="Censimento dell'agricoltura 2020"),
        _voce("Suolo consumato", c["consumato"], COLORI["consumato"], consumo="perm. + rev.",
              nota=f"ISPRA 2025: {_n(c['consumato_pct'], 1)}% del territorio; comprende il fotovoltaico a terra (reversibile)"),
        _voce("Colture per il biometano, in tutto (stima)", c["mais"], COLORI["mais"],
              nota=(f"30.500 t/anno di colture energetiche dichiarate, a 45–60 t/ha. A Pavia solo "
                    f"{_n(c['mais_pavia'], 0)} ha (dato del Comune): il resto è in altri comuni. Circa il "
                    f"{_n(100 - c['mais_quota_nuova'] * 100, 0)}% serviva già al biogas del 2012"),
              testo=f"{_n(round(c['mais_min'], -1), 0)}–{_n(round(c['mais_max'], -1), 0)} ha · a Pavia {_n(c['mais_pavia'], 0)}"),
        _voce("Fotovoltaico a terra, tutti i progetti", c["fv_tutti"], COLORI["fv"], consumo="reversibile",
              nota="Realizzati, autorizzati e Contessa (agrivoltaico, non conteggiato da ISPRA); esclusi i respinti"),
        _voce("Tetto del 3% della SAU", c["tetto"], COLORI["tetto"], contorno=True,
              nota="Unico per fotovoltaico a terra, accumuli e biometano, o uno per tipologia: il testo non è chiaro"),
        _voce("Tetti adatti al fotovoltaico", c["tetti_max"], COLORI["tetti"],
              nota=f"ISPRA 2026: tra {_n(c['tetti_min'], 0)} e {_n(c['tetti_max'], 0)} ha",
              testo=f"{_n(c['tetti_min'], 0)}–{_n(c['tetti_max'], 0)} ha"),
        _voce("Accumuli, tutti i progetti", c["bess_tutti"], COLORI["bess"], consumo="permanente", nota="Compresi EAGLE 1 e Lauzacco BESS"),
        _voce("Impianto di biometano", c["biometano"], COLORI["biometano"], consumo="permanente", nota="Solo l'impianto, senza i campi"),
    ]
    return sorted(v, key=lambda x: -x["ha"])


def gruppo_tetto_unico(c: dict) -> list[tuple[str, list[dict]]]:
    """Lettura A dell'art. 8, c. 3: un solo tetto per fotovoltaico a terra, accumuli e biometano insieme."""
    t = _voce("Tetto del 3%", c["tetto"], COLORI["tetto"], contorno=True, nota="3% della superficie agricola (SAU)")
    aut = _voce("Autorizzati: FV + accumuli + biometano", c["unico_aut"], "#c98a1a",
                nota=(f"FV {_n(c['fv_aut'], 1)} ha + accumuli {_n(c['bess_aut'], 1)} ha + biometano "
                      f"{_n(c['biometano'], 1)} ha, in zona agricola"))
    tutti = _voce("Con Contessa ed EAGLE 1", c["unico_aut"] + c["unico_in_corso"], "#f0d39a",
                  nota="Progetti in istruttoria in zona agricola")
    return [("Tetto unico<br><span style='font-weight:normal'>FV a terra + accumuli + biometano</span>", [t, aut, tutti])]


def gruppi_tetto(c: dict) -> list[tuple[str, list[dict]]]:
    """Lettura B dell'art. 8, c. 3: un tetto per ciascuna tipologia."""
    t = _voce("Tetto del 3%", c["tetto"], COLORI["tetto"], contorno=True, nota="3% della superficie agricola (SAU)")
    fv = [t, _voce("Autorizzato in zona agricola", c["fv_aut"], COLORI["fv"],
                   nota="Cjase Sterpet, Crimea, Risano, compensazione, San Mauro e Selvuzzis; superficie complessiva"),
          _voce("Con Contessa", c["fv_aut"] + c["fv_contessa"], COLORI["fv_chiaro"],
                nota="Contessa è agrivoltaico: va chiarito se conta come «moduli a terra»")]
    bess = [t, _voce("Autorizzati", c["bess_aut"], COLORI["bess"], nota="Enel, RNE14 (solo il BESS), Aukera"),
            _voce("Con EAGLE 1", c["bess_aut"] + c["bess_in_corso"], COLORI["bess_chiaro"],
                  nota="Lauzacco BESS è in zona H2 e non conta")]
    bio = [t, _voce("Impianto", c["biometano"], COLORI["biometano"], nota="I campi per l'alimentazione non contano")]
    return [("Fotovoltaico a terra<br><span style='font-weight:normal'>consumo reversibile</span>", fv),
            ("Accumuli<br><span style='font-weight:normal'>consumo permanente</span>", bess),
            ("Biometano<br><span style='font-weight:normal'>consumo permanente</span>", bio)]
