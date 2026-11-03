"""Ritaglia sul Friuli Venezia Giulia due estrazioni OpenStreetMap fatte con overpass-turbo.

  - linee elettriche ad alta tensione (power=line): tiene 132, 220 e 380/400 kV
  - fotovoltaici a terra (power=generator, generator:source=solar, esclusi i tetti), da 0,5 ha in su

Il confine è l'unione dei comuni di data/territorio/geo/comuni_fvg.geojson, allargata di circa 1 km.
Le geometrie sono semplificate a circa 30 m per tenere leggero il file.

Uso (solo in locale, serve shapely):
    python scripts/ritaglia_osm_fvg.py linee.geojson fotovoltaico.geojson data/territorio/geo/osm_fvg.geojson

Dati © OpenStreetMap contributors, licenza ODbL.
"""
import json
import math
import sys
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
TENSIONI = {132, 220, 380, 400}
HA_MIN = 0.5


def _kv(v):
    try:
        return max(int(x) for x in str(v).split(";")) // 1000
    except (TypeError, ValueError):
        return None


def _ha(geom):
    lat = geom.centroid.y
    return geom.area * 111320 * math.cos(math.radians(lat)) * 110540 / 1e4


def main(linee, fv, out):
    comuni = json.load(open(ROOT / "data" / "territorio" / "geo" / "comuni_fvg.geojson", encoding="utf-8"))
    fvg = unary_union([shape(f["geometry"]).buffer(0) for f in comuni["features"]]).buffer(0.012)
    feats = []
    for f in json.load(open(linee, encoding="utf-8"))["features"]:
        p = f["properties"]
        kv = _kv(p.get("voltage"))
        if f["geometry"]["type"] != "LineString" or kv not in TENSIONI:
            continue
        g = shape(f["geometry"])
        if not g.intersects(fvg):
            continue
        g = g.intersection(fvg).simplify(0.0003)
        if g.is_empty:
            continue
        parti = [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString"]
        for parte in parti:
            feats.append({"type": "Feature", "geometry": {"type": "LineString",
                                                          "coordinates": [[round(x, 5), round(y, 5)] for x, y in parte.coords]},
                          "properties": {"tipo": "linea", "osm_id": p["@id"], "tensione_kv": 380 if kv == 400 else kv,
                                         "nome": p.get("name"), "ref": p.get("ref"), "gestore": p.get("operator")}})
    n_fv = 0
    for f in json.load(open(fv, encoding="utf-8"))["features"]:
        p = f["properties"]
        if p.get("location") == "roof" or p.get("building") or f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            continue
        g = shape(f["geometry"]).buffer(0)
        if not g.intersects(fvg) or _ha(g) < HA_MIN:
            continue
        c = g.centroid
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(c.x, 5), round(c.y, 5)]},
                      "properties": {"tipo": "fv", "osm_id": p["@id"], "nome": p.get("name"), "gestore": p.get("operator"),
                                     "potenza": p.get("generator:output:electricity"), "ha": round(_ha(g), 2)}})
        n_fv += 1
    fc = {"type": "FeatureCollection", "fonte": "© OpenStreetMap contributors, ODbL; estrazione overpass-turbo del 03/11/2026",
          "features": feats}
    json.dump(fc, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(feats) - n_fv, "tratti di linea,", n_fv, "fotovoltaici a terra salvati in", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
