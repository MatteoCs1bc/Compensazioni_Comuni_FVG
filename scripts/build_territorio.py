"""Costruisce le tabelle territoriali usate dall'app a partire da data/territorio/raw.

Va rilanciato solo quando cambiano i dati grezzi:
    python scripts/build_territorio.py
Richiede shapely e pyproj (requirements-dev.txt); l'app non li usa.
"""
import json
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from shapely.geometry import Point, shape, mapping
from shapely.ops import unary_union, transform

T = Path(__file__).resolve().parents[1] / "data" / "territorio"
RAW = T / "raw"


def norm(s: str) -> str:
    return " ".join(str(s).replace("’", "'").lower().split())


comuni = json.load(open(T / "geo" / "comuni_fvg.geojson"))
poly = {f["properties"]["comune"]: shape(f["geometry"]) for f in comuni["features"]}
nomi = {norm(k): k for k in poly}


def comune_di(lon, lat):
    p = Point(lon, lat)
    for k, g in poly.items():
        if g.contains(p):
            return k
    return None


# --- BESS dal WFS regionale (RIS_ENERG:prog_impaue_v_bess_public) ---
to84 = Transformer.from_crs("EPSG:6708", "EPSG:4326", always_xy=True).transform
raw = json.load(open(RAW / "bess_raw.geojson"))
grp = {}
for f in raw["features"]:
    p = f["properties"]
    g = grp.setdefault(p["fascicolo"], {"p": p, "geoms": [], "kw": None, "stato": set()})
    g["geoms"].append(shape(f["geometry"]))
    if p["potenza_elettrica_picco"]:
        g["kw"] = max(g["kw"] or 0, p["potenza_elettrica_picco"])
    if (p["stato"] or "").strip():
        g["stato"].add(p["stato"].strip())
feats, rows = [], []
for fasc, g in grp.items():
    geom = transform(to84, unary_union(g["geoms"]))
    c = geom.centroid
    mw = (g["kw"] or 0) / 1000 or None
    nota, conta = "", True
    if fasc == "2549":
        mw, nota = 137.75, "Dato regionale 1.377,5 MW corretto in 137,75 MW (stima APE FVG per Pavia di Udine)"
    if fasc == "2560":
        conta, nota = False, "Stessa area della pratica 2559 (Basiliano Uno): alternativa, non sommata"
    if fasc == "2559":
        nota = "Stessa area della pratica 2560: si conta una sola volta"
    com = comune_di(c.x, c.y)
    r = dict(fascicolo=fasc, progetto=g["p"]["nome_progetto"], mw=mw, stato="/".join(sorted(g["stato"])) or "n.d.",
             numero_decreto=g["p"]["numero_decreto"] or "", comune=com, lon=round(c.x, 5), lat=round(c.y, 5),
             conta_nel_totale=conta, nota=nota)
    rows.append(r)
    feats.append({"type": "Feature", "properties": r, "geometry": mapping(geom)})
bess = pd.DataFrame(rows).sort_values("mw", ascending=False)
bess.to_csv(T / "bess_progetti.csv", index=False)
json.dump({"type": "FeatureCollection", "features": feats}, open(T / "geo" / "bess_progetti.geojson", "w"))

# --- AU fotovoltaico/agrivoltaico >= 1 MW 2025-2026 (ricognizione BUR) ---
db = pd.read_excel(RAW / "au_fv_2025_2026_ricognizione.xlsx", sheet_name="Database progetti")
db = db[[c for c in db.columns if not str(c).startswith("Unnamed")]]
db = db.drop(columns=[c for c in db.columns if "priorit" in str(c).lower() or "commerc" in str(c).lower()], errors="ignore")
db.to_csv(T / "au_fv_2025_2026.csv", index=False)
rel = pd.read_excel(RAW / "au_fv_2025_2026_ricognizione.xlsx", sheet_name="Relazione Comune-Progetto")
rel = rel[["Comune", "ID progetto", "Impianto/progetto", "Potenza progetto (MW)", "Tipologia", "Data AU"]]

# --- indicatori per comune ---
sint = pd.read_csv(RAW / "rete_comuni_sintesi.csv")
sint["key"] = sint["comune"].map(norm)
b = bess[bess.conta_nel_totale & bess.comune.notna()].groupby("comune").agg(bess_n=("fascicolo", "count"), bess_mw=("mw", "sum"))
b.index = b.index.map(norm)
rel["key"] = rel["Comune"].map(norm)
au = rel.groupby("key").agg(au_fv_n=("ID progetto", "nunique"), au_fv_mw_progetti=("Potenza progetto (MW)", "sum"))
pp = pd.read_csv(RAW / "progetti_per_area.csv")
pp["comune"] = [comune_di(x, y) for x, y in zip(pp.lon, pp.lat)]
pp.to_csv(T / "progetti_regionali_con_comune.csv", index=False)
pc = pp.dropna(subset=["comune"]).assign(key=lambda d: d.comune.map(norm)).pivot_table(
    index="key", columns="categoria", values="potenza_mw", aggfunc="sum", fill_value=0)
pc.columns = [f"mw_progetti_{c.lower()}" for c in pc.columns]
pcn = pp.dropna(subset=["comune"]).assign(key=lambda d: d.comune.map(norm)).groupby("key").size().rename("progetti_nel_comune")
opp = pd.read_csv(T / "opposizioni_locali.csv")
out = sint.set_index("key").join(b).join(au).join(pc).join(pcn)
out["opposizione_censita"] = [any(norm(c) in norm(l) for l in opp.luogo) for c in out.comune]
for c in ["bess_n", "bess_mw", "au_fv_n", "au_fv_mw_progetti", "progetti_nel_comune"] + list(pc.columns):
    out[c] = out[c].fillna(0)
out.reset_index(drop=True).to_csv(T / "comuni_indicatori.csv", index=False)
print("BESS:", len(bess), "pratiche,", round(bess[bess.conta_nel_totale].mw.sum(), 1), "MW;",
      "comuni:", len(out), "; progetti senza comune:", pp.comune.isna().sum())
print(bess[["progetto", "mw", "comune"]].to_string())
