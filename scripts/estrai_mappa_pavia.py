"""Ricava i poligoni degli impianti FER di Pavia di Udine dalla mappa Insiel del Comune.

La mappa «FER al 30-09-2026» (PDF, scala 1:20.000) contiene un'immagine raster georeferenziata:
i vertici sono indicati nel cartiglio in ETRS89 / UTM 33N (EPSG:25833).
  NO: E 363609, N 5095254    SE: E 371564, N 5090642
Lo script isola i poligoni colorati (verde, giallo, arancio), li abbina al numero dell'elenco
comunale tramite il punto centrale letto a vista sulla mappa, e li converte in WGS84.

Uso (solo in locale, non serve all'app):
    pip install pymupdf opencv-python-headless pyproj
    python scripts/estrai_mappa_pavia.py "Mappa al 30-09.pdf" data/pavia/impianti_pavia.geojson

Precisione: un pixel vale circa 2,35 m; i contorni sono semplificati a circa 5 m.
Le superfici ricavate coincidono con quelle dell'elenco comunale entro il 5-10%.
"""
import json
import sys

import cv2
import numpy as np
import pymupdf
from pyproj import Transformer

NO = (363609, 5095254)
SE = (371564, 5090642)

# Punto interno (pixel dell'immagine 3384 x 1962) letto sulla mappa, maschera di colore, id e nome.
# La numerazione è quella dell'elenco FER del Comune; "0a" e "0b" sono i due impianti del 2012.
POLIGONI = [
    ("8", "verde", (255, 893), "8", None),
    ("4a", "verde", (1043, 524), "4", None),
    ("4b", "verde", (950, 1295), "4", None),
    ("4c", "verde", (815, 1345), "4", None),
    ("4d", "verde", (758, 1522), "4", None),
    ("10", "verde", (1378, 479), "10", None),
    ("0a", "verde", (2512, 663), "0a", "San Mauro (2012)"),
    ("0b", "verde", (2320, 875), "0b", "Selvuzzis (2012)"),
    ("2a", "arancio", (2224, 601), "2", None),
    ("2b", "arancio", (2017, 750), "2", None),
    ("17", "arancio", (376, 1314), "17", None),
    ("18", "arancio", (1666, 1180), "18", None),
    ("21", "arancio", (1403, 1246), "21", None),
    ("19", "arancio", (1701, 1632), "19", None),
    ("5", "giallo", (1907, 184), "5", None),
    ("12", "giallo", (1281, 276), "12", None),
    ("7", "giallo", (2275, 1266), "7", None),
    ("13", "giallo", (2966, 1590), "13", None),
    ("1", "verde_chiaro", (1607, 1669), "1", None),
    ("16", "verde_chiaro", (1418, 1461), "16", None),
    ("20a", "verde_chiaro", (1291, 1409), "20", None),
    ("20b", "verde_chiaro", (1319, 1352), "20", None),
    ("20c", "verde_chiaro", (1330, 1390), "20", None),
    ("terna_ampl", "verde_chiaro", (1341, 1477), "terna_ampl", "Ampliamento stazione Terna"),
    ("terna", "verde_scuro", (1501, 1639), "terna", "Stazione Terna «Udine Sud»"),
]
# Impianti senza poligono distinguibile: solo un punto (pixel)
PUNTI = [("3", (1465, 1557), "3", None)]


def maschere(im):
    b, g, r = (im[..., i].astype(int) for i in range(3))
    return {
        "verde": (g > 130) & (g < 200) & (r < 45) & (b < 45),
        "verde_chiaro": (g > 240) & (r < 30) & (b < 40),
        "verde_scuro": (g > 130) & (g <= 195) & (r < 40) & (b < 40),
        "arancio": (r > 235) & (g > 140) & (g < 190) & (b < 50),
        "giallo": (r > 225) & (g > 225) & (b < 70),
    }


def main(pdf, out):
    doc = pymupdf.open(pdf)
    xref = max(doc[0].get_images(full=True), key=lambda i: i[2] * i[3])[0]
    pix = pymupdf.Pixmap(doc, xref)
    if pix.n > 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    im = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)[..., ::-1]
    h, w = im.shape[:2]
    sx, sy = (SE[0] - NO[0]) / w, (NO[1] - SE[1]) / h
    tr = Transformer.from_crs(25833, 4326, always_xy=True)

    def lonlat(x, y):
        lon, lat = tr.transform(NO[0] + (x + 0.5) * sx, NO[1] - (y + 0.5) * sy)
        return [round(lon, 6), round(lat, 6)]

    lab = {}
    for k, m in maschere(im).items():
        m = m.astype(np.uint8) * 255
        if k == "verde_chiaro":   # i poligoni adiacenti sono separati solo dal bordo: niente chiusura
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
            lab[k] = cv2.connectedComponents(m, connectivity=4)[1]
        else:
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            lab[k] = cv2.connectedComponents(m)[1]

    feats = []
    for pid, k, (x, y), rif, nome in POLIGONI:
        L = lab[k]
        win = L[max(0, y - 15):y + 16, max(0, x - 15):x + 16].ravel()
        win = win[win > 0]
        if not len(win):
            raise SystemExit(f"{pid}: nessun poligono {k} vicino a {x},{y}")
        comp = np.bincount(win).argmax()
        mask = (L == comp).astype(np.uint8)
        cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)
        c = cv2.approxPolyDP(c, 2.0, True)[:, 0, :]
        ring = [lonlat(px, py) for px, py in c]
        ring.append(ring[0])
        ha = round(float(mask.sum()) * sx * sy / 1e4, 2)
        cy, cx = np.argwhere(mask).mean(0)
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"id": pid, "rif": rif, "nome": nome, "ha_mappa": ha,
                                     "centro": lonlat(cx, cy)}})
    for pid, (x, y), rif, nome in PUNTI:
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": lonlat(x, y)},
                      "properties": {"id": pid, "rif": rif, "nome": nome, "ha_mappa": None, "centro": lonlat(x, y)}})
    fc = {"type": "FeatureCollection",
          "fonte": "Comune di Pavia di Udine, cartografia Insiel «FER al 30-09-2026» (scala 1:20.000, ETRS89/UTM 33N), "
                   "poligoni ricavati con scripts/estrai_mappa_pavia.py",
          "features": feats}
    json.dump(fc, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    for f in feats:
        p = f["properties"]
        print(p["id"], p["ha_mappa"], p["centro"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
