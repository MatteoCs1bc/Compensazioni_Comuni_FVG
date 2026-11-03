"""Cabine elettriche e centrali del FVG da un'estrazione OpenStreetMap (overpass-turbo).

Interrogazione usata (03/11/2026):
    [out:json][timeout:180];
    area["ISO3166-2"="IT-36"]->.fvg;
    ( nwr["power"="substation"](area.fvg); nwr["power"="plant"](area.fvg); );
    out body; >; out skel qt;

Classi:
  stazione   stazioni della rete di trasmissione gestite da Terna (o «transmission» senza gestore)
  primaria   cabine primarie AT/MT (substation=distribution o 132/60 kV)
  secondaria cabine secondarie MT/BT (substation=minor_distribution o senza tipo né tensione; in FVG
             vengono in gran parte dalla cartografia tecnica regionale CTRN)
  altra      cabine industriali, ferroviarie (RFI) e di centrale, anche ad alta tensione
  centrale   power=plant, con fonte e potenza

Per le cabine primarie aggiunge l'area di cabina primaria che le contiene (codice e-distribuzione,
data/territorio/geo/aree_cabine_primarie.geojson) e le sezioni con inversione di flusso della cabina
più vicina entro 3 km (data/territorio/raw/inversioni_cabine.csv).

Uso (solo in locale, serve shapely):
    python scripts/ritaglia_osm_cabine.py export.geojson data/territorio/geo/osm_cabine_fvg.geojson

Dati © OpenStreetMap contributors, licenza ODbL.
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "data" / "territorio"


def _kv(v):
    try:
        return max(int(x) for x in str(v).split(";") if x.strip().isdigit()) // 1000
    except ValueError:
        return None


def _mw(v):
    m = re.match(r"\s*([\d.,]+)\s*(k|M|G)?W", str(v or ""))
    if not m:
        return None
    x = float(m.group(1).replace(",", "."))
    return round(x * {"k": 0.001, "M": 1, "G": 1000, None: 1e-6}[m.group(2)], 3)


def _m(a, b):
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 110540)


def classe(p):
    sub, kv = p.get("substation"), _kv(p.get("voltage"))
    if sub == "disused":
        return None
    terna = "terna" in str(p.get("operator", "")).lower()
    if terna or (sub == "transmission" and not p.get("operator")):
        return "stazione"
    if sub in ("transmission", "industrial", "generation", "traction", "converter") or (kv or 0) >= 220:
        return "altra"
    if sub == "distribution" or kv in (132, 60, 130, 150):
        op = str(p.get("operator") or "").lower()
        distributore = not op or any(x in op for x in ("distribuzione", "enel", "acegas", "aps", "hera", "seb"))
        return "primaria" if distributore else "altra"
    if sub == "minor_distribution" or (sub is None and kv is None) or (kv or 99) <= 30 and sub in (None, "yes"):
        return "secondaria"
    return "altra"


def main(src, out):
    comuni = json.load(open(T / "geo" / "comuni_fvg.geojson", encoding="utf-8"))
    fvg = unary_union([shape(f["geometry"]).buffer(0) for f in comuni["features"]]).buffer(0.005)
    aree = [(f["properties"]["codice"], shape(f["geometry"]).buffer(0))
            for f in json.load(open(T / "geo" / "aree_cabine_primarie.geojson", encoding="utf-8"))["features"]]
    inv = list(csv.DictReader(open(T / "raw" / "inversioni_cabine.csv", encoding="utf-8")))
    feats, n = [], {}
    for f in json.load(open(src, encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("power") not in ("substation", "plant"):
            continue
        g = shape(f["geometry"])
        c = g.representative_point() if g.geom_type != "Point" else g
        if not fvg.contains(c):
            continue
        xy = [round(c.x, 5), round(c.y, 5)]
        if p["power"] == "plant":
            q = {"classe": "centrale", "nome": p.get("name"), "gestore": p.get("operator"),
                 "fonte": p.get("plant:source"), "mw": _mw(p.get("plant:output:electricity"))}
        else:
            k = classe(p)
            if k is None:
                continue
            if k == "secondaria":
                q = {"classe": k}
                if p.get("name"):
                    q["nome"] = p["name"]
            else:
                q = {"classe": k, "nome": p.get("name"), "gestore": p.get("operator"),
                     "tensione_kv": _kv(p.get("voltage")), "ref_terna": p.get("ref:terna"), "tipo_osm": p.get("substation")}
                if k == "primaria":
                    q["area"] = next((cod for cod, a in aree if a.contains(Point(c.x, c.y))), None)
                    vicine = sorted(((_m(xy, (float(r["lon"]), float(r["lat"]))), r) for r in inv), key=lambda t: t[0])
                    if vicine and vicine[0][0] < 3000:
                        r = vicine[0][1]
                        q["inversione"] = {"cabina": r["cabina"], "sezioni": int(r["sezioni"]), "oltre_5": int(r["oltre_5"])}
        q = {k2: v for k2, v in q.items() if v is not None}
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": xy}, "properties": q})
        n[q["classe"]] = n.get(q["classe"], 0) + 1
    fc = {"type": "FeatureCollection", "fonte": "© OpenStreetMap contributors, ODbL; estrazione overpass-turbo del 03/11/2026",
          "features": feats}
    json.dump(fc, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(n, "->", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
