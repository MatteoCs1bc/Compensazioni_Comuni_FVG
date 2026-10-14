# Stato della rete elettrica in Friuli-Venezia Giulia, comune per comune

Pacchetto dati autosufficiente. Contiene tutto ciò che serve per valutare la
situazione della rete di distribuzione di un singolo comune friulano, più la
documentazione necessaria a interpretarlo senza altro contesto.

**Chi legge questo file per la prima volta legga prima la sezione "Cosa non si
può dire".** È la parte che evita di costruire analisi su dati che non
esistono.

---

## 1. I file, e a cosa servono

### Tabelle principali

| File | Righe | Contenuto |
|---|---|---|
| `rete_comuni_sintesi.csv` | 215 | **Una riga per comune.** È il punto di partenza |
| `rete_comuni_dettaglio.csv` | 347 | Una riga per coppia comune-cabina: i comuni divisi compaiono più volte |

### Tabelle di supporto

| File | Righe | Contenuto |
|---|---|---|
| `aree_cabine_primarie.csv` | 59 | Le aree di influenza delle cabine primarie: codice, gestore, superficie |
| `saturazione_aree.csv` | 59 | Domanda di connessione per area, scomposta per tecnologia |
| `progetti_per_area.csv` | 244 | Ogni progetto autorizzato o in istruttoria, con la sua area |
| `inversioni_flusso.csv` | 66 | Sezioni AT/MT con inversione di flusso in FVG, 2025 |
| `inversioni_cabine.csv` | 39 | Le stesse, aggregate per cabina, **con coordinate** |
| `inversioni_regioni.csv` | 18 | Confronto nazionale: sezioni invertite per regione |
| `comuni_cabine.csv` | 347 | Corrispondenza grezza comune-area con superfici di sovrapposizione |

### Geometrie (GeoJSON, EPSG:4326)

| File | Elementi | Contenuto |
|---|---|---|
| `geo/comuni_fvg.geojson` | 215 | Confini comunali. Chiave di join: `comune` |
| `geo/aree_cabine_primarie.geojson` | 59 | Aree di influenza. Chiave di join: `codice` |

### Contesto regionale

| File | Contenuto |
|---|---|
| `rete_consistenza.csv` | Clienti, cabine secondarie, km di linea |
| `rete_potenza_connessa.csv`, `rete_fer_per_fonte.csv` | Potenza installata e rinnovabile |
| `rete_trasformatori_stato.csv` | Saturazione dei trasformatori AT/MT per fascia di colore |
| `rete_trasformatori_province.csv` | Trasformatori per provincia |
| `rete_aree_critiche.csv` | Comuni per livello di criticità |
| `rete_interventi_programmati.csv` | Ampliamenti e nuove cabine per provincia |
| `rete_distributori.csv` | I quattro distributori attivi in regione |
| `rete_interconnessioni.csv` | Linee transfrontaliere |
| `rete_burden_sharing.csv` | Avanzamento verso il target 2030 |
| `rete_accumuli_bess.csv` | Pipeline degli accumuli |

### Codice

`dataset_rete_comuni.py` costruisce le due tabelle principali dalle altre.
`etl_cabine.py`, `etl_saturazione.py`, `etl_comuni_cabine.py`, `etl_inversioni.py`
producono le tabelle di supporto dai dati grezzi.

---

## 2. Schema di `rete_comuni_sintesi.csv`

Una riga per comune. È la tabella da cui partire.

| Colonna | Tipo | Significato |
|---|---|---|
| `comune` | testo | Nome del comune. **Chiave di join** con `comuni_fvg.geojson` |
| `aree_cabina` | intero | Su quante cabine primarie ricade il territorio comunale |
| `area_principale` | testo | Codice della cabina che ne serve la porzione maggiore |
| `quota_area_principale` | 0–1 | Quale frazione del comune sta sotto quella cabina |
| `gestori` | testo | Distributori competenti, separati da virgola |
| `km2_comune` | numero | Superficie del comune |
| `progetti_sulle_aree` | intero | Progetti FER sulle aree che servono il comune |
| `mw_richiesti_sulle_aree` | numero | MW di richieste di connessione sulle stesse aree |
| `cabine_invertite` | intero | Cabine con inversione di flusso fra quelle che lo servono |
| `sezioni_invertite` | intero | Sezioni AT/MT invertite almeno l'1% del tempo |
| `sezioni_oltre_5pct` | intero | Di quelle, quante oltre il 5% del tempo |
| `comune_diviso` | booleano | Vero se ricade su più di una cabina |
| `flusso_invertito` | booleano | Vero se almeno una sezione si è invertita |
| `stato_indicativo` | testo | Sintesi qualitativa — **vedi avvertenza sotto** |

**Attenzione su `progetti_sulle_aree` e `mw_richiesti_sulle_aree`.** Non sono i
progetti *del comune*: sono quelli che insistono sull'intera area di influenza
della cabina, che si estende oltre i confini comunali. Un comune piccolo dentro
un'area molto sollecitata eredita un numero alto senza averne responsabilità.
Per attribuire i progetti al comune serve una join spaziale su
`progetti_per_area.csv`, che ha le coordinate di ciascuno.

**Attenzione su `stato_indicativo`.** È una lettura costruita da noi con soglie
arbitrarie (inversione oltre il 5% → "frequente"; oltre 200 MW richiesti →
"forte pressione"). Non è una classificazione ufficiale e non ha valore
tecnico. Le colonne numeriche sottostanti sono il dato; questa è
un'interpretazione, e chi la usa può rifarla diversamente.

---

## 3. Come i dati si collegano fra loro

```
comuni_fvg.geojson ──[comune]──┐
                               ├──> rete_comuni_dettaglio ──[aggregazione]──> rete_comuni_sintesi
aree_cabine_primarie ─[codice]─┘
        │
        ├──[codice]──> saturazione_aree ──> domanda di connessione per area
        │                    ↑
        │              [join spaziale]
        │                    │
        │              progetti_per_area (lon/lat di ogni progetto)
        │
        └──[join spaziale su lon/lat]── inversioni_cabine ── inversioni_flusso
```

**Il punto di raccordo non era ovvio.** I due strati sulle cabine nascono
separati: le aree convenzionali hanno la geometria e un codice
(`AC001E01003`) ma nessun nome; l'elenco delle inversioni ha il nome
(`CODROIPO`) ma nessuna coordinata. Si parlano grazie a un fatto: **i nomi
delle cabine sono toponimi**. Dal nome si risale al comune, dal comune al
centroide, dal centroide — con una join spaziale — all'area convenzionale.
Tutte e 39 le cabine con inversione si agganciano così alla loro area.

Quindici nomi non coincidevano con un comune e sono stati risolti a mano
(dizionario `ALIAS_COMUNE` in `etl_inversioni.py`): abbreviazioni come
`S.DANIELE`, frazioni come `GIAIS` che sta ad Aviano, zone industriali come
`ZAULE` a Trieste e `SCHIAVETTI` a Monfalcone.

---

## 4. Cosa non si può dire, e perché

Questa sezione è la più importante del documento.

**La hosting capacity residua per cabina non è pubblica.** E-distribuzione
pubblica il totale regionale — 485 MW al 2025, senza considerare le richieste
in pipeline — e la saturazione dei trasformatori aggregata per fasce di colore
(35 verdi, 27 arancioni, 9 gialli, 4 rossi su 75 totali). Non esiste il dato
area per area. Chiunque affermi "in questo comune ci sono X MW liberi" sta
inventando.

**La capacità di trasporto delle linee non è pubblicata.**

**Le cabine secondarie non hanno dati pubblici.** Sono 10.607 in regione:
nessuna posizione, nessuno stato.

**Le posizioni delle cabine primarie sono approssimate.** Sono i centroidi dei
comuni che danno il nome alla cabina, non le coordinate dell'impianto. Servono
a leggere la geografia del fenomeno, non a progettare.

**Le aree di influenza sono aggiornate al 30/09/2025** e sono state ritagliate
sul confine regionale: coprono 7.664 km² su 7.932 di superficie regionale.

**Il tasso di realizzazione conta.** Storicamente circa metà della capacità
autorizzata non viene mai costruita. La domanda di connessione va letta come
pressione, non come impianti futuri.

### Che cosa si può dire, allora

Due cose, entrambe solide:

1. **Pressione autorizzativa**: quanti MW di progetti insistono su una porzione
   di rete. Indicatore indiretto ma affidabile — dove ci sono molte richieste,
   la capacità libera tende a essere poca.
2. **Inversione di flusso**: indicatore fisico di saturazione *già avvenuta*.
   Se il flusso si inverte, la generazione distribuita ha superato il consumo
   locale in quelle ore. Non è una previsione, è una misura.

---

## 5. Il vincolo che conta per le comunità energetiche

In Italia, produttori e consumatori devono stare **sotto la stessa cabina
primaria** per condividere energia in una comunità energetica rinnovabile.

Le aree di influenza **non seguono i confini comunali**: **97 comuni su 215
sono divisi fra due e cinque cabine diverse**. In quei comuni una CER su base
comunale non può coprire tutto il territorio — due frazioni dello stesso comune
possono non poter condividere energia fra loro.

La colonna `comune_diviso` in `rete_comuni_sintesi.csv` lo segnala. Per sapere
quale parte del territorio sta sotto quale cabina serve
`rete_comuni_dettaglio.csv`, che ha la superficie di sovrapposizione riga per
riga.

---

## 6. I numeri d'insieme, per orientarsi

| Indicatore | Valore |
|---|---|
| Comuni | 215 |
| Aree di influenza delle cabine primarie | 59 |
| Comuni su una sola cabina | 118 |
| Comuni divisi fra più cabine | 97 |
| Domanda di connessione totale | 2.844 MW |
| Aree con almeno un progetto | 43 su 59 |
| Concentrazione nelle prime 5 aree | 63% della domanda |
| Cabine con inversione di flusso | 39 su 45 |
| Sezioni AT/MT invertite | 66 |
| di cui oltre il 5% del tempo | 45 (68%) |
| Comuni serviti da cabine con inversione | 187 su 215 |
| Hosting capacity regionale residua | 485 MW |
| Trasformatori AT/MT in zona rossa | 4 su 75 |
| Distributori attivi | 4 |

**La geografia dell'inversione è istruttiva.** Il flusso si inverte in due aree
opposte per ragioni opposte: in **Carnia** (Ampezzo, Ovaro, Tolmezzo,
Chiusaforte) perché l'idroelettrico produce più di quanto le valli consumino, e
nella **bassa pianura** (Codroipo, Palmanova, Latisana) per il fotovoltaico.
Stesso effetto sulla rete, cause diverse — e implicazioni diverse, perché
l'idroelettrico è stagionale e prevedibile, il fotovoltaico è diurno e
concentrato.

---

## 7. Fonti

* **Aree convenzionali delle cabine primarie** — dataset dei distributori,
  aggiornamento 30/09/2025. Pubblico.
* **Inversioni di flusso** — e-distribuzione, "Elenco delle sezioni AT/MT per
  le quali è stata riscontrata inversione del flusso di energia per almeno 1% e
  5% del tempo nell'anno 2025", pubblicato il 28 febbraio 2026. Documento
  nazionale, 1.728 sezioni in 18 regioni.
* **Progetti FER** — portale regionale dei procedimenti autorizzativi FVG.
* **Consistenza di rete, saturazione, interventi** — audizioni della IV
  Commissione del Consiglio regionale FVG, 21 aprile 2026 (e-distribuzione,
  Terna, AcegasApsAmga, SECAB).
* **Confini comunali** — portale cartografico regionale FVG (EAGLE).

Tutte le fonti sono pubbliche. Le elaborazioni (join spaziali, aggregazioni,
geolocalizzazione delle cabine dai toponimi) sono nostre e il codice è incluso.
