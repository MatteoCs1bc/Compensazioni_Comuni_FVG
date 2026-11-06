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
    return {
        "superficie": float(consumo.superficie_ha), "consumato": float(consumo.consumato_2025_ha),
        "consumato_pct": float(consumo.consumato_2025_pct), "sau": sau, "sat": s["agricoltura"]["sat_ha"],
        "tetto": tetto,
        "fv_aut": somma(agr, "fv"), "fv_incerta": somma(imp[imp.zona == "incerta"], "fv"),
        "fv_contessa": somma(agr, "fv", ("in_corso",)), "fv_tutti": float(imp[imp.tipologia == "fv"].ha.sum()),
        "bess_aut": somma(agr, "bess"), "bess_in_corso": somma(agr, "bess", ("in_corso",)),
        "bess_tutti": float(imp[imp.tipologia == "bess"].ha.sum()),
        "biometano": somma(agr, "biometano"),
        "mais": m["tonnellate_anno"] * m["quota_insilato"] / m["resa_t_ha"],
        "tetti_min": float(consumo.tetti_fv_min_ha), "tetti_max": float(consumo.tetti_fv_max_ha),
        "tetti_mw_min": float(consumo.tetti_fv_min_ha) * s["tetti_mw_per_ha"],
        "tetti_mw_max": float(consumo.tetti_fv_max_ha) * s["tetti_mw_per_ha"],
        "realizzati": float(imp[imp.get("realizzato", pd.Series(False, index=imp.index)).fillna(False).astype(bool)].ha.sum()),
        "netto_2006_2025": float(sum(consumo[f"netto_{p}"] for p, _ in PERIODI)),
        "netto_2021_2025": float(sum(consumo[f"netto_{p}"] for p in ("2021_2022", "2022_2023", "2023_2024", "2024_2025"))),
    }


def ripartizione_territorio(c: dict, s: dict) -> pd.DataFrame:
    """Territorio comunale diviso in SAU (per coltura), suolo consumato (impianti FER realizzati e resto) e altro.
    SAU dal censimento 2020 e suolo consumato ISPRA 2025: fonti diverse, la somma è un ordine di grandezza."""
    righe = [("Territorio comunale", "", c["superficie"])]
    righe.append(("Superficie agricola (SAU)", "Territorio comunale", c["sau"]))
    resto_sau = c["sau"]
    for col in s["colture"]:
        v = c["sau"] * col["pct"] / 100
        resto_sau -= v
        righe.append((col["nome"], "Superficie agricola (SAU)", v))
    righe.append(("Altre colture", "Superficie agricola (SAU)", resto_sau))
    righe.append(("Suolo consumato", "Territorio comunale", c["consumato"]))
    righe.append(("Impianti energetici realizzati", "Suolo consumato", c["realizzati"]))
    righe.append(("Edifici, strade, aree produttive e altro", "Suolo consumato", c["consumato"] - c["realizzati"]))
    righe.append(("Resto del territorio", "Territorio comunale", c["superficie"] - c["sau"] - c["consumato"]))
    return pd.DataFrame(righe, columns=["voce", "padre", "ha"])


def rispetto_sau(c: dict, s: dict) -> pd.DataFrame:
    """Ogni superficie in percentuale della SAU comunale, raggruppata per tipo."""
    sau = c["sau"]
    r = [(col["nome"], "Colture (censimento 2020)", sau * col["pct"] / 100) for col in s["colture"][:3]]
    r += [("Suolo consumato in totale", "Consumo di suolo (ISPRA)", c["consumato"]),
          ("Nuovo consumo 2006–2025", "Consumo di suolo (ISPRA)", c["netto_2006_2025"]),
          ("Nuovo consumo 2021–2025", "Consumo di suolo (ISPRA)", c["netto_2021_2025"]),
          ("Mais per il biometano (stima)", "Impianti", c["mais"]),
          ("Fotovoltaico a terra con Contessa", "Impianti", c["fv_aut"] + c["fv_contessa"]),
          ("Fotovoltaico a terra autorizzato", "Impianti", c["fv_aut"]),
          ("Accumuli con EAGLE 1", "Impianti", c["bess_aut"] + c["bess_in_corso"]),
          ("Impianto di biometano", "Impianti", c["biometano"]),
          ("Tetti adatti al fotovoltaico (max)", "Alternative", c["tetti_max"])]
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

def _voce(nome, valore, colore, contorno=False, nota="", testo=None):
    """Una superficie da disegnare. contorno=True: solo bordo tratteggiato (un limite, non un'occupazione)."""
    return {"nome": nome, "ha": float(valore), "colore": colore, "contorno": contorno, "nota": nota,
            "testo": testo or ha(valore)}


def _etichetta(v):
    return f"<b>{v['nome']}</b><br>{v['testo']}"


def _hover(v):
    return f"<b>{v['nome']}</b><br>{v['testo']}" + (f"<br><i>{v['nota']}</i>" if v["nota"] else "")


def _quadrato(fig, x0, y0, lato, v):
    import plotly.graph_objects as go
    x1, y1 = x0 + lato, y0 + lato
    if v["contorno"]:
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(color=v["colore"], width=2, dash="dash"),
                      fillcolor="rgba(0,0,0,0)", layer="above")
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
        _quadrato(fig, cx - lt / 2, 0, lt, v)
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
    xl = 1.0 + 30 / lato_px
    for v, lt, y in zip(voci, lati, ys):
        fig.add_shape(type="line", x0=lt, y0=lt, x1=xl, y1=y, line=dict(color="#7b8794", width=1))
        fig.add_annotation(x=xl, y=y, text=_etichetta(v), showarrow=False, xanchor="left", yanchor="middle",
                           align="left", **_box(v["colore"]))
    return _layout(fig, -0.01, xl + ETICHETTA_W / lato_px, -0.01, max(1.0, ys[0] + passo / 2) + 0.01, lato_px)


def figura_pannelli(gruppi: list[tuple[str, list[dict]]], lato_px: int = 150):
    """Più gruppi di quadrati annidati, affiancati alla stessa scala; etichette in elenco sotto ogni pannello."""
    import plotly.graph_objects as go
    fig = go.Figure()
    u = max(math.sqrt(v["ha"]) for _, vv in gruppi for v in vv)
    larg = max(1.0, ETICHETTA_W / lato_px) + 40 / lato_px
    riga, titolo_h = ETICHETTA_H / lato_px, 34 / lato_px
    n_max = max(len(vv) for _, vv in gruppi)
    for j, (titolo, voci) in enumerate(gruppi):
        x0 = j * larg
        voci = sorted(voci, key=lambda v: -v["ha"])
        for v in voci:
            if not v["contorno"]:
                _quadrato(fig, x0, 0, math.sqrt(v["ha"]) / u, v)
        for v in voci:
            if v["contorno"]:
                _quadrato(fig, x0, 0, math.sqrt(v["ha"]) / u, v)
        fig.add_annotation(x=x0, y=1.0 + 8 / lato_px, text=f"<b>{titolo}</b>", showarrow=False, xanchor="left",
                           yanchor="bottom", font=dict(color=TESTO, size=14))
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
                 "Impianti": "#e0a800", "Alternative": COLORI["tetti"]}


def figura_territorio(df: pd.DataFrame):
    """Il territorio comunale come un quadrato diviso in parti proporzionali agli ettari (treemap)."""
    import plotly.graph_objects as go
    col = {"Territorio comunale": "#f4f6f1", "Superficie agricola (SAU)": COLORI["agricola"], "Cereali": "#9cc45a",
           "Piante industriali (soprattutto soia)": "#b5d47e", "Vite": "#6f9a2e", "Prati permanenti e pascoli": "#c9e0a0",
           "Altre colture": "#d8e8bd", "Suolo consumato": COLORI["consumato"],
           "Impianti energetici realizzati": COLORI["fv"], "Edifici, strade, aree produttive e altro": "#a7adb6",
           "Resto del territorio": COLORI["territorio"]}
    tot = df.loc[df.voce == "Territorio comunale", "ha"].iloc[0]
    testo = [f"{ha(v)} · {_n(v / tot * 100, 1)}% del territorio" for v in df.ha]
    fig = go.Figure(go.Treemap(labels=df.voce, parents=df.padre, values=df.ha, branchvalues="total",
                               marker=dict(colors=[col.get(v, "#ccc") for v in df.voce], line=dict(color="white", width=2)),
                               text=testo, texttemplate="<b>%{label}</b><br>%{text}", textfont=dict(color=TESTO, size=13),
                               hovertemplate="<b>%{label}</b><br>%{text}<br>%{percentParent:.1%} di «%{parent}»<extra></extra>",
                               tiling=dict(pad=3), pathbar=dict(visible=False), maxdepth=3, sort=True))
    fig.update_layout(height=480, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      uniformtext=dict(minsize=11, mode="hide"),
                      hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12), align="left"))
    return fig


def figura_rispetto_sau(df: pd.DataFrame, tetto_pct: float = 3.0):
    """Barre orizzontali: ogni superficie in percentuale della SAU; linea tratteggiata sul tetto del 3%."""
    import plotly.graph_objects as go
    d = df.iloc[::-1]
    fig = go.Figure(go.Bar(x=d.pct_sau, y=d.voce, orientation="h", marker_color=[COLORI_GRUPPO[g] for g in d.gruppo],
                           text=[f"{_n(p, 1)}%  ·  {ha(h)}" for p, h in zip(d.pct_sau, d.ha)], textposition="outside",
                           textfont=dict(color=TESTO), customdata=d.gruppo,
                           hovertemplate="<b>%{y}</b><br>%{x:.1f}% della SAU<br>%{customdata}<extra></extra>"))
    fig.add_vline(x=tetto_pct, line=dict(color=COLORI["tetto"], width=1.5, dash="dash"), layer="below",
                  annotation_text="tetto 3%", annotation_position="top", annotation_font_color=TESTO)
    fig.update_layout(height=40 * len(d) + 60, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title="% della SAU comunale",
                      hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12)))
    fig.update_xaxes(range=[0, max(d.pct_sau) * 1.35], ticksuffix="%")
    return fig


def voci_consumi(c: dict) -> list[dict]:
    """Il suolo consumato del comune e, dentro, il nuovo consumo e gli impianti (realizzati e in progetto)."""
    return [
        _voce("Suolo consumato al 2025", c["consumato"], COLORI["consumato"], nota="ISPRA 2026: edifici, strade, aree produttive, impianti"),
        _voce("Nuovo consumo 2006–2025", c["netto_2006_2025"], "#5d6570", nota="Netto: al netto dei ripristini"),
        _voce("Impianti energetici realizzati", c["realizzati"], COLORI["fv"],
              nota="Cjase Sterpet, Risano, San Mauro e Selvuzzis, BESS Enel, sottostazione, biometano; superficie complessiva"),
        _voce("Nuovo consumo 2021–2025", c["netto_2021_2025"], COLORI["mais"], nota="Gli anni dei grandi fotovoltaici"),
        _voce("Contessa ed EAGLE 1 (in istruttoria)", c["fv_contessa"] + c["bess_in_corso"], COLORI["bess_chiaro"],
              nota="Se autorizzati, si aggiungerebbero al suolo occupato"),
    ]


# --- composizioni per la scheda di Pavia -----------------------------------------------------------------------

def voci_panoramica(c: dict, territorio: bool = False) -> list[dict]:
    v = []
    if territorio:
        v.append(_voce("Territorio comunale", c["superficie"], COLORI["territorio"], nota="ISPRA 2026"))
    v += [
        _voce("Superficie agricola (SAU)", c["sau"], COLORI["agricola"], nota="Censimento dell'agricoltura 2020"),
        _voce("Suolo già consumato", c["consumato"], COLORI["consumato"],
              nota=f"ISPRA 2025: {_n(c['consumato_pct'], 1)}% del territorio; include il fotovoltaico a terra"),
        _voce("Mais per il biometano (stima)", c["mais"], COLORI["mais"],
              nota="Ipotesi: metà delle 50.000 t/anno è insilato, 55 t/ha; non tutto a Pavia",
              testo=f"circa {_n(round(c['mais'], -1), 0)} ha"),
        _voce("Fotovoltaico a terra, tutti i progetti", c["fv_tutti"], COLORI["fv"],
              nota="Realizzati, autorizzati e Contessa; esclusi i progetti respinti"),
        _voce("Tetto del 3% (per tipologia)", c["tetto"], COLORI["tetto"], contorno=True,
              nota="3% della SAU: vale separatamente per FV a terra, accumuli, biometano"),
        _voce("Tetti adatti al fotovoltaico", c["tetti_max"], COLORI["tetti"],
              nota=f"ISPRA 2026: tra {_n(c['tetti_min'], 0)} e {_n(c['tetti_max'], 0)} ha",
              testo=f"{_n(c['tetti_min'], 0)}–{_n(c['tetti_max'], 0)} ha"),
        _voce("Accumuli, tutti i progetti", c["bess_tutti"], COLORI["bess"], nota="Compresi EAGLE 1 e Lauzacco BESS"),
        _voce("Impianto di biometano", c["biometano"], COLORI["biometano"], nota="Solo l'impianto, senza i campi"),
    ]
    return sorted(v, key=lambda x: -x["ha"])


def gruppi_tetto(c: dict) -> list[tuple[str, list[dict]]]:
    t = _voce("Tetto del 3%", c["tetto"], COLORI["tetto"], contorno=True, nota="3% della superficie agricola (SAU)")
    fv = [t, _voce("Autorizzato in zona agricola", c["fv_aut"], COLORI["fv"],
                   nota="Cjase Sterpet, Crimea, Risano, compensazione, San Mauro e Selvuzzis; superficie complessiva"),
          _voce("Con Contessa", c["fv_aut"] + c["fv_contessa"], COLORI["fv_chiaro"],
                nota="Contessa è agrivoltaico: va chiarito se conta come «moduli a terra»")]
    bess = [t, _voce("Autorizzati", c["bess_aut"], COLORI["bess"], nota="Enel, RNE14 (solo il BESS), Aukera"),
            _voce("Con EAGLE 1", c["bess_aut"] + c["bess_in_corso"], COLORI["bess_chiaro"],
                  nota="Lauzacco BESS è in zona H2 e non conta")]
    bio = [t, _voce("Impianto", c["biometano"], COLORI["biometano"], nota="I campi per l'alimentazione non contano")]
    return [("Fotovoltaico a terra", fv), ("Accumuli", bess), ("Biometano", bio)]
