"""Simulazione del fondo comunale per i cittadini: contributi a fondo perduto o fondo rotativo."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class EsitoAnno:
    anno: int
    versato: float          # risorse entrate nel fondo quell'anno
    erogato: float          # contributi o prestiti erogati
    famiglie: int
    famiglie_cumulate: int
    rientri: float = 0.0    # solo fondo rotativo
    cassa_fine: float = 0.0
    credito_in_essere: float = 0.0


def fondo_perduto(capitale_iniziale: float, quota_annua: float, anni: int, contributo_medio: float,
                  costi_gestione: float = 0.0) -> list[EsitoAnno]:
    """Ogni anno si spende quello che c'è, al netto dei costi di gestione (quota sul versato)."""
    out, cum, cassa = [], 0, 0.0
    for a in range(1, anni + 1):
        versato = quota_annua + (capitale_iniziale if a == 1 else 0.0)
        cassa += versato * (1 - costi_gestione)
        n = int(cassa // contributo_medio) if contributo_medio > 0 else 0
        erog = n * contributo_medio
        cassa -= erog
        cum += n
        out.append(EsitoAnno(a, versato, erog, n, cum, cassa_fine=cassa))
    return out


def fondo_rotativo(capitale_iniziale: float, quota_annua: float, anni: int, prestito_medio: float,
                   durata_rimborso: int, insolvenza: float = 0.03, costi_gestione: float = 0.01) -> list[EsitoAnno]:
    """Prestiti a tasso zero: rimborso in rate annuali costanti a partire dall'anno successivo.

    insolvenza: quota del capitale prestato che non rientra.
    costi_gestione: commissione annua del gestore (banca o confidi) sul credito in essere.
    """
    out, cum, cassa = [], 0, 0.0
    coorti: list[tuple[int, float]] = []  # (anno di erogazione, importo)
    for a in range(1, anni + 1):
        versato = quota_annua + (capitale_iniziale if a == 1 else 0.0)
        rientri = sum(imp * (1 - insolvenza) / durata_rimborso for y, imp in coorti if y < a <= y + durata_rimborso)
        credito = sum(imp * max(0, durata_rimborso - (a - 1 - y)) / durata_rimborso for y, imp in coorti if a - 1 - y < durata_rimborso)
        cassa += versato + rientri - credito * costi_gestione
        n = int(max(cassa, 0) // prestito_medio) if prestito_medio > 0 else 0
        erog = n * prestito_medio
        cassa -= erog
        if erog:
            coorti.append((a, erog))
        cum += n
        credito_fine = sum(imp * max(0, durata_rimborso - (a - y)) / durata_rimborso for y, imp in coorti)
        out.append(EsitoAnno(a, versato, erog, n, cum, rientri, cassa, credito_fine))
    return out


def famiglie_per_euro(esiti: list[EsitoAnno]) -> float:
    tot = sum(e.versato for e in esiti)
    return esiti[-1].famiglie_cumulate / tot * 10000 if tot else math.nan
