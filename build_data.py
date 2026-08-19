"""
Genera i file JSON statici per il frontend (docs/data/) a partire dai dati
scaricati da scraper_ufc.py. Va rilanciato ogni volta che si vogliono dati
aggiornati (rilancia anche lo scraping se la cache CSV non c'e' o e' vecchia).

Il dettaglio di ogni lottatore (infobox + storico incontri) viene
pre-scaricato qui per tutti i lottatori con una pagina Wikipedia, cosi' il
sito finale e' completamente statico (nessun server Python da tenere
acceso) — ogni lottatore diventa un file JSON separato in
docs/data/lottatori/<slug>.json, scaricato dal browser solo quando serve.
"""

import json
import re
import time
from pathlib import Path

import pandas as pd

from scraper_ufc import scarica_dettaglio_lottatore, scarica_eventi, scarica_roster

WEB_DATA = Path(__file__).parent / "docs" / "data"
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


# Roster attuale (scarica_roster) elenca solo chi e' sotto contratto oggi —
# leggende ritirate come Khabib o Jon Jones (al momento del ritiro) non ci
# sono. Le aggiungiamo a mano: e' una lista curata, non uno scraping
# automatico, quindi va estesa manualmente se manca qualcuno di importante.
LEGGENDE = [
    ("Khabib Nurmagomedov", "https://en.wikipedia.org/wiki/Khabib_Nurmagomedov"),
    ("Jon Jones", "https://en.wikipedia.org/wiki/Jon_Jones"),
    ("Georges St-Pierre", "https://en.wikipedia.org/wiki/Georges_St-Pierre"),
    ("Anderson Silva", "https://en.wikipedia.org/wiki/Anderson_Silva"),
    ("BJ Penn", "https://en.wikipedia.org/wiki/BJ_Penn"),
    ("Chuck Liddell", "https://en.wikipedia.org/wiki/Chuck_Liddell"),
    ("Randy Couture", "https://en.wikipedia.org/wiki/Randy_Couture"),
    ("Demetrious Johnson", "https://en.wikipedia.org/wiki/Demetrious_Johnson_(fighter)"),
    ("Daniel Cormier", "https://en.wikipedia.org/wiki/Daniel_Cormier"),
    ("Cain Velasquez", "https://en.wikipedia.org/wiki/Cain_Velasquez"),
    ("Ronda Rousey", "https://en.wikipedia.org/wiki/Ronda_Rousey"),
    ("Brock Lesnar", "https://en.wikipedia.org/wiki/Brock_Lesnar"),
    ("Michael Bisping", "https://en.wikipedia.org/wiki/Michael_Bisping"),
    ("Vitor Belfort", "https://en.wikipedia.org/wiki/Vitor_Belfort"),
    ("Tito Ortiz", "https://en.wikipedia.org/wiki/Tito_Ortiz"),
    ("Matt Hughes", "https://en.wikipedia.org/wiki/Matt_Hughes_(fighter)"),
    ("Frankie Edgar", "https://en.wikipedia.org/wiki/Frankie_Edgar"),
    ("Junior dos Santos", "https://en.wikipedia.org/wiki/Junior_dos_Santos"),
    ("José Aldo", "https://en.wikipedia.org/wiki/Jos%C3%A9_Aldo"),
    ("Forrest Griffin", "https://en.wikipedia.org/wiki/Forrest_Griffin"),
]

CATEGORIA_LEGGENDE = "Leggende (ex campioni)"


def _righe_leggende():
    return pd.DataFrame(
        [{"categoria": CATEGORIA_LEGGENDE, "nome": nome, "link": link, "slug": _slug_da_link(link)} for nome, link in LEGGENDE]
    )


def _record_da_storico_json(path):
    if not path.exists():
        return None
    storico = json.loads(path.read_text(encoding="utf-8")).get("storico") or []
    if not storico:
        return None
    vinte = sum(1 for f in storico if str(f.get("res.", "")).strip().lower() == "win")
    perse = sum(1 for f in storico if str(f.get("res.", "")).strip().lower() == "loss")
    return f"{vinte}–{perse}"


def genera_roster_e_eventi():
    roster = scarica_roster()
    eventi = scarica_eventi()

    roster = roster.assign(slug=roster["link"].apply(lambda l: _slug_da_link(l) if isinstance(l, str) else None))
    roster = pd.concat([roster, _righe_leggende()], ignore_index=True)
    eventi = eventi.assign(tipo=eventi["evento"].apply(_tipo_evento))

    (WEB_DATA / "eventi.json").write_text(
        json.dumps(_pulisci_per_json(eventi), ensure_ascii=False, indent=None), encoding="utf-8"
    )
    print(f"eventi.json: {len(eventi)} eventi")
    return roster


def scrivi_roster_json(roster):
    """Va chiamata DOPO genera_dettagli_lottatori: solo allora lo storico
    delle leggende e' in cache e possiamo calcolarne il record vinte-perse
    (le leggende non hanno un record_mma dalla pagina roster, a differenza
    degli attuali)."""
    mask = roster["categoria"] == CATEGORIA_LEGGENDE
    roster.loc[mask, "record_mma"] = roster.loc[mask, "slug"].apply(
        lambda s: _record_da_storico_json(WEB_DATA_LOTTATORI / f"{s}.json")
    )
    (WEB_DATA / "roster.json").write_text(
        json.dumps(_pulisci_per_json(roster), ensure_ascii=False, indent=None), encoding="utf-8"
    )
    print(f"roster.json: {len(roster)} lottatori ({mask.sum()} leggende)")


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
    scrivi_roster_json(roster)
