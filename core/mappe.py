"""Mappe interattive con rete elettrica (OpenStreetMap), progetti ed esistente.

Usato dalla pagina «Quadro FVG» (scala regionale) e, per la legenda e le linee, dalla scheda di Pavia di Udine.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "territorio" / "geo"

COLORI_TENSIONE = {380: "#6a1b9a", 220: "#1565c0", 132: "#00838f"}
COLORI_CATEGORIA = {"Solare": "#f2a900", "Accumuli": "#e64a19", "Bioenergie": "#6d8b2f", "Idroelettrico": "#0277bd"}
STATI_FVG = ["Realizzato", "In costruzione", "Autorizzato", "In istruttoria", "Stato non indicato"]
ESISTENTE = {"Realizzato"}
STATO_BESS = {"in esercizio": "Realizzato", "autorizzato": "Autorizzato", "conclusa": "Autorizzato",
              "in corso": "In istruttoria", "n.d.": "Stato non indicato"}
TESTO = "#1f2933"


def legende(fig, titolo1: str, titolo2: str | None = None):
    """Legende leggibili anche con il tema scuro: testo scuro su fondo bianco.
    La prima in alto a sinistra sopra la mappa; la seconda (rete e dati OSM) sotto la mappa, in orizzontale.
    Va chiamata dopo aver fissato l'altezza della figura."""
    base = dict(font=dict(color=TESTO, size=12), bgcolor="rgba(255,255,255,0.93)", bordercolor="#b0bec5",
                borderwidth=1, orientation="v", itemsizing="constant", groupclick="togglegroup", tracegroupgap=2)
    fig.update_layout(legend=dict(base, title=dict(text=f"<b>{titolo1}</b>", font=dict(color=TESTO)),
                                  x=0.01, y=0.99, xanchor="left", yanchor="top"))
    if titolo2:
        # la seconda legenda sta sotto la mappa, in orizzontale, per non coprire gli impianti
        fig.update_layout(legend2=dict(base, title=dict(text=f"<b>{titolo2}</b>", font=dict(color=TESTO), side="top"),
                                       orientation="h", x=0, y=0, xanchor="left", yanchor="top", entrywidth=0),
                          margin=dict(b=110), height=(fig.layout.height or 600) + 110)
    fig.update_layout(hoverlabel=dict(bgcolor="white", font=dict(color=TESTO, size=12), align="left"))
    return fig


def tracce_linee(fig, feats: list[dict], legenda: str = "legend2"):
    """Una traccia per livello di tensione, con nome e codice della linea al passaggio del mouse."""
    import plotly.graph_objects as go
    linee = [f for f in feats if f["properties"]["tipo"] == "linea"]
    for kv in sorted({f["properties"]["tensione_kv"] or 0 for f in linee}, reverse=True):
        lon, lat, txt = [], [], []
        for f in linee:
            p = f["properties"]
            if (p["tensione_kv"] or 0) != kv:
                continue
            t = (f"<b>Linea {kv} kV</b>" + (f"<br>{p['nome']}" if p.get("nome") else "")
                 + (f"<br>Codice {p['ref']}" if p.get("ref") else "") + (f"<br>{p['gestore']}" if p.get("gestore") else "")
                 + "<br><i>OpenStreetMap</i>")
            for x, y in f["geometry"]["coordinates"]:
                lon.append(x); lat.append(y); txt.append(t)
            lon.append(None); lat.append(None); txt.append(None)
        fig.add_trace(go.Scattermap(lon=lon, lat=lat, mode="lines", name=f"Linea {kv} kV",
                                    line=dict(color=COLORI_TENSIONE.get(kv, "#546e7a"), width=3 if kv >= 220 else 2),
                                    hovertext=txt, hoverinfo="text", legend=legenda))

CABINE = {  # classe: (nome in legenda, colore, dimensione, opacità)
    "stazione": ("Stazioni AT (Terna)", "#000000", 14, 1.0),
    "primaria": ("Cabine primarie AT/MT", "#c2185b", 10, 0.95),
    "altra": ("Cabine industriali e di centrale", "#8d6e63", 7, 0.85),
    "secondaria": ("Cabine secondarie MT/BT", "#607d8b", 4, 0.6),
}
SINGOLARE = {"stazione": "Stazione AT (Terna)", "primaria": "Cabina primaria AT/MT", "altra": "Cabina industriale o di centrale"}
COLORI_FONTE = {"solar": "#f2a900", "hydro": "#0277bd", "biogas": "#6d8b2f", "biomass": "#6d8b2f",
                "gas": "#424242", "coal": "#424242", "waste": "#795548"}
NOMI_FONTE = {"solar": "solare", "hydro": "idroelettrica", "biogas": "biogas", "biomass": "biomasse", "gas": "gas",
              "coal": "carbone", "waste": "rifiuti"}


def cabine_fvg() -> dict:
    """Stazioni, cabine e centrali da OpenStreetMap (scripts/ritaglia_osm_cabine.py)."""
    with open(GEO / "osm_cabine_fvg.geojson", encoding="utf-8") as f:
        return json.load(f)


def dati_aree() -> pd.DataFrame:
    """Aree di cabina primaria con MW richiesti e sezioni con inversione di flusso (dalle cabine OSM agganciate)."""
    a = pd.read_csv(ROOT / "data" / "territorio" / "raw" / "saturazione_aree.csv")
    inv = {}
    for f in cabine_fvg()["features"]:
        p = f["properties"]
        if p["classe"] == "primaria" and p.get("area"):
            d = inv.setdefault(p["area"], {"cabine": [], "sezioni": 0})
            d["cabine"].append(p.get("nome") or "senza nome")
            d["sezioni"] += p.get("inversione", {}).get("sezioni", 0)
    a["cabine_osm"] = a.codice.map(lambda c: ", ".join(inv.get(c, {}).get("cabine", [])) or "non mappata su OSM")
    a["sezioni_invertite"] = a.codice.map(lambda c: inv.get(c, {}).get("sezioni", 0))
    return a


def tracce_aree(fig, dati: pd.DataFrame):
    import plotly.graph_objects as go
    gj = json.load(open(GEO / "aree_cabine_primarie.geojson", encoding="utf-8"))
    fig.add_trace(go.Choroplethmap(
        geojson=gj, featureidkey="properties.codice", locations=dati.codice, z=dati.mw_richiesti,
        colorscale="Blues", marker=dict(opacity=0.35, line=dict(width=1.2, color="#37474f")),
        colorbar=dict(title=dict(text="MW richiesti<br>sull'area", font=dict(color=TESTO)), tickfont=dict(color=TESTO),
                      x=0.99, xanchor="right", y=0.99, yanchor="top", len=0.45, thickness=12,
                      bgcolor="rgba(255,255,255,0.93)", outlinewidth=0),
        hovertext=[f"<b>Area di cabina primaria {r.codice}</b><br>{r.gestore} · {_mw(r.area_km2)} km²"
                   f"<br>Cabina: {r.cabine_osm}<br>Progetti sull'area: {int(r.progetti)} · {_mw(r.mw_richiesti)} MW richiesti"
                   + (f"<br>Sezioni con inversione di flusso: {r.sezioni_invertite}" if r.sezioni_invertite else "")
                   for r in dati.itertuples()],
        hoverinfo="text", name="Aree di cabina primaria", showlegend=True, legend="legend2"))


def tracce_cabine(fig, feats: list[dict], classi=("stazione", "primaria", "altra", "secondaria"), legenda="legend2"):
    import plotly.graph_objects as go
    aree = None
    for k in ["secondaria", "altra", "primaria", "stazione"]:   # le più importanti disegnate sopra
        if k not in classi:
            continue
        x = [f for f in feats if f["properties"]["classe"] == k]
        if not x:
            continue
        nome, colore, size, op = CABINE[k]
        if k == "secondaria":
            hover = [f"Cabina secondaria{(' ' + f['properties']['nome']) if f['properties'].get('nome') else ''}"
                     "<br><i>OpenStreetMap / CTRN</i>" for f in x]
        else:
            if k == "primaria" and aree is None:
                aree = dati_aree().set_index("codice")
            hover = []
            for f in x:
                p = f["properties"]
                t = f"<b>{p.get('nome') or SINGOLARE[k]}</b><br>{SINGOLARE[k]}"
                t += (f" · {p['tensione_kv']} kV" if p.get("tensione_kv") else "") + (f"<br>{p['gestore']}" if p.get("gestore") else "")
                if k == "primaria" and p.get("area") in getattr(aree, "index", []):
                    r = aree.loc[p["area"]]
                    t += f"<br>Area {p['area']}: {_mw(r.mw_richiesti)} MW richiesti, {int(r.progetti)} progetti"
                if p.get("inversione"):
                    i = p["inversione"]
                    t += f"<br>Inversione di flusso: {i['sezioni']} sezioni ({i['oltre_5']} oltre il 5% del tempo)"
                hover.append(t + "<br><i>OpenStreetMap</i>")
        fig.add_trace(go.Scattermap(
            lon=[f["geometry"]["coordinates"][0] for f in x], lat=[f["geometry"]["coordinates"][1] for f in x],
            mode="markers", name=nome, marker=dict(size=size, color=colore, opacity=op),
            hovertext=hover, hoverinfo="text", legend=legenda))


def tracce_centrali(fig, feats: list[dict], legenda="legend2"):
    import plotly.graph_objects as go
    x = [f for f in feats if f["properties"]["classe"] == "centrale"]
    if not x:
        return
    mw = [f["properties"].get("mw") for f in x]
    fig.add_trace(go.Scattermap(
        lon=[f["geometry"]["coordinates"][0] for f in x], lat=[f["geometry"]["coordinates"][1] for f in x],
        mode="markers", name="Centrali esistenti (colore = fonte)",
        marker=dict(size=[(m or 1) ** 0.5 * 2.2 + 6 for m in mw], opacity=0.85,
                    color=[COLORI_FONTE.get(f["properties"].get("fonte"), "#9e9e9e") for f in x]),
        hovertext=[f"<b>{f['properties'].get('nome') or 'Centrale'}</b>"
                   f"<br>Fonte: {NOMI_FONTE.get(f['properties'].get('fonte'), 'non indicata')}"
                   + (f" · {_mw(f['properties']['mw'])} MW" if f["properties"].get("mw") else "")
                   + (f"<br>{f['properties']['gestore']}" if f["properties"].get("gestore") else "")
                   + "<br><i>OpenStreetMap</i>" for f in x],
        hoverinfo="text", legend=legenda))


# ---------------------------------------------------------------------------
# Scala regionale
# ---------------------------------------------------------------------------
def osm_fvg() -> dict:
    with open(GEO / "osm_fvg.geojson", encoding="utf-8") as f:
        return json.load(f)


def progetti_fvg() -> pd.DataFrame:
    """Progetti del portale regionale RIS_ENERG con coordinate; per gli accumuli il registro BESS corretto."""
    p = pd.read_csv(ROOT / "data" / "territorio" / "progetti_regionali_con_comune.csv")
    p = p[p.categoria != "Accumuli"][["categoria", "nome", "potenza_mw", "superficie_ha", "stato", "comune", "lon", "lat"]]
    b = pd.read_csv(ROOT / "data" / "territorio" / "bess_progetti.csv")
    b = b[b.conta_nel_totale]
    b = pd.DataFrame({"categoria": "Accumuli", "nome": b.progetto, "potenza_mw": b.mw, "superficie_ha": None,
                      "stato": b.stato.map(STATO_BESS).fillna("Stato non indicato"), "comune": b.comune,
                      "lon": b.lon, "lat": b.lat})
    df = pd.concat([p, b], ignore_index=True)
    df["stato"] = df.stato.where(df.stato.isin(STATI_FVG), "Stato non indicato")
    return df


def _mw(x) -> str:
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".").removesuffix(",0")


LIVELLI_DEFAULT = {"linee", "fv_osm", "cabine", "centrali"}


def figura_fvg(df: pd.DataFrame, osm: dict | None, categorie: list[str], stati: list[str],
               livelli: set[str] | None = None, stile: str = "open-street-map"):
    """Livelli: aree, linee, cabine (stazioni, primarie, industriali), secondarie, centrali, fv_osm."""
    import plotly.graph_objects as go
    livelli = LIVELLI_DEFAULT if livelli is None else set(livelli)
    fig = go.Figure()
    if "aree" in livelli:
        tracce_aree(fig, dati_aree())
    if osm and "linee" in livelli:
        tracce_linee(fig, osm["features"])
    cab = cabine_fvg()["features"] if livelli & {"cabine", "secondarie", "centrali"} else []
    classi = (("stazione", "primaria", "altra") if "cabine" in livelli else ()) + (("secondaria",) if "secondarie" in livelli else ())
    if classi:
        tracce_cabine(fig, cab, classi)
    if "centrali" in livelli:
        tracce_centrali(fig, cab)
    if osm and "fv_osm" in livelli:
        fv = [f["properties"] | {"lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1]}
              for f in osm["features"] if f["properties"]["tipo"] == "fv"]
        if fv:
            d = pd.DataFrame(fv)
            fig.add_trace(go.Scattermap(
                lon=d.lon, lat=d.lat, mode="markers", name="Fotovoltaico a terra esistente",
                marker=dict(size=(d.ha.clip(lower=0.5) ** 0.5) * 3 + 4, color="#455a64", opacity=0.75),
                hovertext=[f"<b>{r.nome or 'Fotovoltaico a terra'}</b>" + (f"<br>{r.gestore}" if r.gestore else "")
                           + f"<br>Circa {_mw(r.ha)} ha" + (f" · {r.potenza}" if r.potenza and r.potenza != "yes" else "")
                           + "<br><i>OpenStreetMap (censimento incompleto)</i>" for r in d.itertuples()],
                hoverinfo="text", legend="legend2"))
    d = df[df.categoria.isin(categorie) & df.stato.isin(stati)]
    for cat, colore in COLORI_CATEGORIA.items():
        x = d[d.categoria == cat]
        if x.empty:
            continue
        size = (x.potenza_mw.fillna(1).clip(lower=0.3) ** 0.5) * 2.6 + 5
        esist = x.stato.isin(ESISTENTE)
        # anello scuro sotto gli impianti esistenti, per distinguerli dai progetti
        if esist.any():
            fig.add_trace(go.Scattermap(lon=x.lon[esist], lat=x.lat[esist], mode="markers",
                                        marker=dict(size=size[esist] + 5, color="#212121"), hoverinfo="skip",
                                        legendgroup=cat, showlegend=False))
        fig.add_trace(go.Scattermap(
            lon=x.lon, lat=x.lat, mode="markers", name=cat, legendgroup=cat,
            marker=dict(size=size, color=colore, opacity=0.9),
            hovertext=[f"<b>{r.nome}</b><br>{cat} · {r.stato}"
                       + (f" · {_mw(r.potenza_mw)} MW" if pd.notna(r.potenza_mw) else "")
                       + (f"<br>{_mw(r.superficie_ha)} ha" if pd.notna(r.superficie_ha) else "")
                       + f"<br>Comune: {r.comune}" for r in x.itertuples()],
            hoverinfo="text"))
    if any(s in ESISTENTE for s in stati):
        fig.add_trace(go.Scattermap(lon=[None], lat=[None], mode="markers", name="Bordo scuro = già realizzato",
                                    marker=dict(size=12, color="#212121"), hoverinfo="skip"))
    fig.update_layout(map=dict(style=stile, center=dict(lat=46.08, lon=13.1), zoom=7.6),
                      margin=dict(l=0, r=0, t=0, b=0), height=640)
    return legende(fig, "Impianti (portale regionale)", "Rete ed esistente (OpenStreetMap)" if livelli else None)
