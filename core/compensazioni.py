"""Calcolo delle compensazioni per impianti FER e accumuli.

Tutte le funzioni sono pure: ricevono numeri, restituiscono numeri.
I parametri di default stanno in data/regole/compensazioni.yaml.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGOLE_PATH = ROOT / "data" / "regole" / "compensazioni.yaml"


def _it(x: float) -> str:
    """Numero con separatore delle migliaia all'italiana."""
    return f"{x:,.0f}".replace(",", ".")


def carica_regole(path: Path = REGOLE_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class ImpiantoProduzione:
    potenza_mw: float
    ore_equivalenti: float
    prezzo_eur_mwh: float
    vita_utile_anni: float = 30
    tasso_sconto: float = 0.0
    autoconsumo_quota: float = 0.0

    @property
    def produzione_mwh_anno(self) -> float:
        return self.potenza_mw * self.ore_equivalenti

    @property
    def proventi_anno(self) -> float:
        return self.produzione_mwh_anno * self.prezzo_eur_mwh

    @property
    def proventi_anno_netti(self) -> float:
        return self.proventi_anno * (1 - self.autoconsumo_quota)

    def fattore_anni(self) -> float:
        """Somma dei fattori di sconto sugli anni di vita utile.

        Con tasso 0 vale semplicemente il numero di anni (metodo APE).
        Anni frazionari: l'ultima frazione pesa in proporzione.
        """
        n = self.vita_utile_anni
        r = self.tasso_sconto
        if r == 0:
            return n
        interi = int(n)
        s = sum(1 / (1 + r) ** t for t in range(1, interi + 1))
        frazione = n - interi
        if frazione:
            s += frazione / (1 + r) ** (interi + 1)
        return s

    @property
    def valore_vita_utile(self) -> float:
        """Valore economico della produzione attesa nella vita utile (base TU FER)."""
        return self.proventi_anno_netti * self.fattore_anni()


@dataclass
class Risultato:
    metodo: str
    nome: str
    natura: str
    annuo: float | None
    totale_min: float
    totale_max: float
    nota: str = ""
    fonte: str = ""

    @property
    def totale_centrale(self) -> float:
        return (self.totale_min + self.totale_max) / 2


def metodi_produzione(imp: ImpiantoProduzione, regole: dict) -> list[Risultato]:
    m = regole["metodi"]
    v = imp.valore_vita_utile
    anni = imp.fattore_anni()
    out = []

    a = m["agenzia"]
    annuo = imp.proventi_anno_netti * a["percentuale"]
    out.append(Risultato("agenzia", a["nome"], a["natura"], annuo, annuo * anni, annuo * anni,
                         f"{a['percentuale']:.0%} dei proventi annui per {imp.vita_utile_anni:g} anni", a["fonte"]))

    for key in ("tufer_pas", "tufer_au"):
        t = m[key]
        out.append(Risultato(key, t["nome"], t["natura"], None, v * t["min"], v * t["max"],
                             f"{t['min']:.0%}–{t['max']:.0%} del valore della produzione nella vita utile", t["fonte"]))

    lr = m["lr_fvg_au"]
    out.append(Risultato("lr_fvg_au", lr["nome"], lr["natura"], imp.proventi_anno_netti * lr["min"],
                         v * lr["min"], v * m["tufer_au"]["max"],
                         f"almeno {lr['min']:.0%}; il tetto resta quello del TU FER ({m['tufer_au']['max']:.0%})", lr["fonte"]))

    b = m["bel_clima"]
    annuo_b = imp.proventi_anno_netti * b["percentuale"]
    out.append(Risultato("bel_clima", b["nome"], b["natura"], annuo_b, annuo_b * anni, annuo_b * anni,
                         f"{b['percentuale']:.0%} dei proventi annui", b["fonte"]))
    return out


def proventi_bess(potenza_mw: float, durata_ore: float, premio_eur_mwh_anno: float,
                  altri_ricavi_eur_mw_anno: float = 0.0) -> float:
    """Proventi annui di un accumulo: premio di capacità sui MWh + altri ricavi per MW."""
    return potenza_mw * durata_ore * premio_eur_mwh_anno + potenza_mw * altri_ricavi_eur_mw_anno


def metodi_bess(potenza_mw: float, regole: dict, capex_eur_mw: float | None = None,
                vita_utile_anni: float | None = None, colocato: bool = False,
                perc_capex: float | None = None, eur_mw_anno: float | None = None,
                eur_mw_una_tantum: float | None = None, durata_ore: float | None = None,
                premio_eur_mwh_anno: float | None = None, altri_ricavi_eur_mw_anno: float | None = None,
                anni_proventi: float | None = None) -> list[Risultato]:
    m = regole["metodi"]
    d = regole["default_fvg"]["bess"]
    capex_eur_mw = capex_eur_mw or d["capex_eur_mw"]
    vita = vita_utile_anni or d["vita_utile_anni"]
    out = []

    pr = m["bess_proventi"]
    h = durata_ore if durata_ore is not None else d["durata_ore"]
    prem = premio_eur_mwh_anno if premio_eur_mwh_anno is not None else d["premio_capacita_eur_mwh_anno"]
    altri = altri_ricavi_eur_mw_anno if altri_ricavi_eur_mw_anno is not None else d["altri_ricavi_eur_mw_anno"]
    n = anni_proventi or d["anni_proventi"]
    prov = proventi_bess(potenza_mw, h, prem, altri)
    out.append(Risultato("bess_proventi", pr["nome"], pr["natura"], prov * pr["default"],
                         prov * pr["min"] * n, prov * pr["max"] * n,
                         f"{pr['min']:.0%}–{pr['max']:.0%} di proventi stimati in {_it(prov)} €/anno "
                         f"({potenza_mw:g} MW × {h:g} h × {_it(prem)} €/MWh + altri ricavi) per {n:g} anni", pr["fonte"]))

    c = m["bess_capex"]
    capex = potenza_mw * capex_eur_mw
    p = perc_capex if perc_capex is not None else c["default"]
    out.append(Risultato("bess_capex", c["nome"], c["natura"], None, capex * c["min"], capex * c["max"],
                         f"{c['min']:.0%}–{c['max']:.0%} di un investimento stimato in {_it(capex)} €; scelto {p:.1%} = {_it(capex * p)} €",
                         c["fonte"]))

    a = m["bess_annuo"]
    q = eur_mw_anno or a["default_eur_mw_anno"]
    out.append(Risultato("bess_annuo", a["nome"], a["natura"], potenza_mw * q,
                         potenza_mw * a["min_eur_mw_anno"] * vita, potenza_mw * a["max_eur_mw_anno"] * vita,
                         f"{_it(a['min_eur_mw_anno'])}–{_it(a['max_eur_mw_anno'])} €/MW/anno per {vita:g} anni; scelto {_it(q)} €/MW/anno = {_it(potenza_mw * q * vita)} €",
                         a["fonte"]))

    u = m["bess_una_tantum"]
    lo, hi = (u["colocated_min"], u["colocated_max"]) if colocato else (u["standalone_min"], u["standalone_max"])
    q2 = eur_mw_una_tantum or u["default_eur_mw"]
    out.append(Risultato("bess_una_tantum", u["nome"], u["natura"], None, potenza_mw * lo, potenza_mw * hi,
                         f"{_it(lo)}–{_it(hi)} €/MW ({'co-locato' if colocato else 'standalone'}); scelto {_it(q2)} €/MW = {_it(potenza_mw * q2)} €",
                         u["fonte"]))
    return out


def valore_scelto_bess(potenza_mw: float, regole: dict, metodo: str, **kw) -> float:
    """Valore puntuale per il metodo BESS scelto (usato da tabelle e test)."""
    d = regole["default_fvg"]["bess"]
    m = regole["metodi"]
    if metodo == "bess_proventi":
        prov = proventi_bess(potenza_mw, kw.get("durata_ore", d["durata_ore"]),
                             kw.get("premio_eur_mwh_anno", d["premio_capacita_eur_mwh_anno"]),
                             kw.get("altri_ricavi_eur_mw_anno", d["altri_ricavi_eur_mw_anno"]))
        return prov * kw.get("percentuale", m["bess_proventi"]["default"]) * kw.get("anni", d["anni_proventi"])
    if metodo == "bess_capex":
        return potenza_mw * kw.get("capex_eur_mw", d["capex_eur_mw"]) * kw.get("perc_capex", m["bess_capex"]["default"])
    if metodo == "bess_annuo":
        return potenza_mw * kw.get("eur_mw_anno", m["bess_annuo"]["default_eur_mw_anno"]) * kw.get("vita_utile_anni", d["vita_utile_anni"])
    if metodo == "bess_una_tantum":
        return potenza_mw * kw.get("eur_mw_una_tantum", m["bess_una_tantum"]["default_eur_mw"])
    raise ValueError(metodo)


def quota_ottenuta(ottenuto_eur: float, imp: ImpiantoProduzione) -> dict:
    """Che percentuale rappresenta una compensazione reale rispetto alle basi di calcolo."""
    return {
        "su_proventi_vita_senza_sconto": ottenuto_eur / (imp.proventi_anno_netti * imp.vita_utile_anni),
        "su_valore_vita_scelto": ottenuto_eur / imp.valore_vita_utile,
    }
