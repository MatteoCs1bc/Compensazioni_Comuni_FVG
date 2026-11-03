"""Ritaglia sull'area di Pavia di Udine due estrazioni OpenStreetMap fatte con overpass-turbo.

  - linee elettriche  (power=line, con tensione)
  - impianti fotovoltaici (power=generator, generator:source=solar)

Tiene le linee e gli impianti che hanno almeno un vertice nel riquadro della mappa di Pavia e scarta i
fotovoltaici che coincidono con un impianto dell'elenco comunale (già disegnato dalla mappa Insiel).

Uso:
    python scripts/ritaglia_osm_pavia.py linee.geojson fotovoltaico.geojson data/pavia/osm_pavia.geojson

Dati © OpenStreetMap contributors, licenza ODbL.
"""
import json
import math
import sys
from pathlib import Path

RIQUADRO = (13.20, 13.38, 45.935, 46.025)   # lon min, lon max, lat min, lat max
DISTANZA_DOPPIONE_M = 150
COMUNE = Path(__file__).resolve().parents[1] / "data" / "pavia" / "impianti_pavia.geojson"


def _punti(c):
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for x in c:
            yield from _punti(x)


def _dentro(f):
    return any(RIQUADRO[0] < x < RIQUADRO[1] and RIQUADRO[2] < y < RIQUADRO[3] for x, y in _punti(f["geometry"]["coordinates"]))


def _m(a, b):
    kx = 111320 * math.cos(math.radians(a[1]))
    return math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * 110540)


def _ha(ring):
    kx, ky = 111320 * math.cos(math.radians(ring[0][1])), 110540
    s = sum(ring[i][0] * kx * ring[i + 1][1] * ky - ring[i + 1][0] * kx * ring[i][1] * ky for i in range(len(ring) - 1))
    return abs(s) / 2 / 1e4


def _kv(v):
    try:
        return int(str(v).split(";")[0]) // 1000
    except (TypeError, ValueError):
        return None


def main(linee, fv, out):
    centri_comune = [f["properties"]["centro"] for f in json.load(open(COMUNE, encoding="utf-8"))["features"]]
    feats = []
    for f in json.load(open(linee, encoding="utf-8"))["features"]:
        p = f["properties"]
        if f["geometry"]["type"] != "LineString" or not _dentro(f):
            continue
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {
            "tipo": "linea", "osm_id": p["@id"], "tensione_kv": _kv(p.get("voltage")), "nome": p.get("name"),
            "ref": p.get("ref"), "gestore": p.get("operator"), "terne": p.get("circuits")}})
    for f in json.load(open(fv, encoding="utf-8"))["features"]:
        p, g = f["properties"], f["geometry"]
        if g["type"] != "Polygon" or not _dentro(f):
            continue
        ring = g["coordinates"][0]
        centro = [sum(c[0] for c in ring) / len(ring), sum(c[1] for c in ring) / len(ring)]
        if any(_m(centro, c) < DISTANZA_DOPPIONE_M for c in centri_comune):
            print("doppione dell'elenco comunale, scartato:", p["@id"])
            continue
        feats.append({"type": "Feature", "geometry": g, "properties": {
            "tipo": "fv", "osm_id": p["@id"], "nome": p.get("name"), "gestore": p.get("operator"),
            "potenza": p.get("generator:output:electricity"), "posizione": p.get("location") or "a terra (non indicato)",
            "ha": round(_ha(ring), 2), "centro": [round(centro[0], 6), round(centro[1], 6)]}})
    fc = {"type": "FeatureCollection", "fonte": "© OpenStreetMap contributors, ODbL; estrazione overpass-turbo del 03/11/2026",
          "features": feats}
    json.dump(fc, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(len(feats), "elementi salvati in", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
