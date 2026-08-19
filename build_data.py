"""
Genera i file JSON statici per il frontend (web/data/) a partire dai dati
scaricati da scraper_ufc.py. Va rilanciato ogni volta che si vogliono dati
aggiornati (rilancia anche lo scraping se la cache CSV non c'e' o e' vecchia).

Il dettaglio di ogni lottatore (infobox + storico incontri) viene
pre-scaricato qui per tutti i lottatori con una pagina Wikipedia, cosi' il
sito finale e' completamente statico (nessun server Python da tenere
acceso) — ogni lottatore diventa un file JSON separato in
web/data/lottatori/<slug>.json, scaricato dal browser solo quando serve.
"""

import json
import re
import time
from pathlib import Path

import pandas as pd

from scraper_ufc import scarica_dettaglio_lottatore, scarica_eventi, scarica_roster

WEB_DATA = Path(__file__).parent / "web" / "data"
WEB_DATA_LOTTATORI = WEB_DATA / "lottatori"
WEB_DATA_LOTTATORI.mkdir(parents=True, exist_ok=True)


def _slug_da_link(link):
    return re.sub(r"[^a-z0-9]+", "-", link.rstrip("/").split("/")[-1].lower()).strip("-")


def _pulisci_per_json(df):
    """NaN non e' JSON valido: lo convertiamo in None."""
    return json.loads(df.where(pd.notna(df), None).to_json(orient="records", force_ascii=False))


def _tipo_evento(nome):
    """Gli eventi UFC hanno due numerazioni separate e indipendenti che si
    accavallano se mostrate senza distinzione (es. 'UFC 293' del 2023 e
    'UFC Fight Night 293' del 2026 sembrano lo stesso evento a chi legge
    solo il numero) — la tag esplicita evita l'equivoco."""
    if re.match(r"^UFC \d+", nome):
        return "Numerato"
    if "Fight Night" in nome:
        return "Fight Night"
    return "Altro"


def genera_roster_e_eventi():
    roster = scarica_roster()
    eventi = scarica_eventi()

    roster = roster.assign(slug=roster["link"].apply(lambda l: _slug_da_link(l) if isinstance(l, str) else None))
    eventi = eventi.assign(tipo=eventi["evento"].apply(_tipo_evento))

    (WEB_DATA / "roster.json").write_text(
        json.dumps(_pulisci_per_json(roster), ensure_ascii=False, indent=None), encoding="utf-8"
    )
    (WEB_DATA / "eventi.json").write_text(
        json.dumps(_pulisci_per_json(eventi), ensure_ascii=False, indent=None), encoding="utf-8"
    )
    print(f"roster.json: {len(roster)} lottatori — eventi.json: {len(eventi)} eventi")
    return roster


def genera_dettagli_lottatori(roster, limite=None, pausa=0.3):
    con_link = roster.dropna(subset=["link"]).reset_index(drop=True)
    if limite:
        con_link = con_link.head(limite)

    fatti, saltati = 0, 0
    for i, riga in con_link.iterrows():
        slug = riga["slug"]
        out_file = WEB_DATA_LOTTATORI / f"{slug}.json"
        if out_file.exists():
            saltati += 1
            continue

        try:
            dettaglio = scarica_dettaglio_lottatore(riga["link"])
        except Exception as e:
            print(f"  [{i+1}/{len(con_link)}] ERRORE {riga['nome']}: {e}")
            continue

        storico = dettaglio["storico"]
        out = {
            "nome": dettaglio["nome"],
            "link": riga["link"],
            "infobox": dettaglio["infobox"],
            "storico": _pulisci_per_json(storico) if not storico.empty else [],
        }
        out_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        fatti += 1
        if fatti % 20 == 0:
            print(f"  [{i+1}/{len(con_link)}] fatti {fatti}, ultimo: {riga['nome']}")
        time.sleep(pausa)

    print(f"Dettagli lottatori: {fatti} scaricati ora, {saltati} gia' in cache. Totale file: {len(list(WEB_DATA_LOTTATORI.glob('*.json')))}")


if __name__ == "__main__":
    roster = genera_roster_e_eventi()
    genera_dettagli_lottatori(roster)
