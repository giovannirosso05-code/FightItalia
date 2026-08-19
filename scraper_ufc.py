"""
Dati lottatori UFC ed eventi da Wikipedia (en.wikipedia.org).

Fonte scelta al posto di UFCStats.com: UFCStats ha introdotto una verifica
anti-bot (proof-of-work in JavaScript) che ne rende lo scraping diretto
fragile e al limite dei termini d'uso del sito. Wikipedia espone dati
equivalenti (record, altezza, reach, categoria di peso, storico incontri)
in tabelle HTML stabili e senza protezioni anti-scraping, a patto di usare
uno User-Agent descrittivo (richiesto dalla policy Wikimedia).

Roster corrente: "List of current UFC fighters" (una tabella per categoria
di peso, una riga per lottatore). Dettaglio lottatore (reach, stance,
storico incontri): pagina Wikipedia individuale, scaricata solo su
richiesta e messa in cache locale, per non scaricare centinaia di pagine
ad ogni avvio.
"""

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://en.wikipedia.org"
ROSTER_URL = f"{BASE}/wiki/List_of_current_UFC_fighters"
EVENTI_URL = f"{BASE}/wiki/List_of_UFC_events"

HEADERS = {
    "User-Agent": "MacinandoMMA/0.1 (progetto personale non commerciale, dati pubblici Wikipedia)"
}

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def _span(cella, attributo):
    """Valore di rowspan/colspan come intero, tollerante ad attributi
    malformati che capitano su alcune pagine Wikipedia (es. su
    List_of_UFC_events una cella ha rowspan='2data-sort-value=\"\"',
    con doppio attributo incollato senza spazio — pandas.read_html si
    rifiuta su questo HTML, qui prendiamo solo le cifre iniziali)."""
    valore = str(cella.get(attributo, "1"))
    m = re.match(r"\s*(\d+)", valore)
    return int(m.group(1)) if m else 1


def _testo_e_link(cella):
    """Il rendering attuale delle pagine Wikipedia usa href assoluti
    (https://en.wikipedia.org/wiki/...) per i wikilink, non piu' solo
    relativi (/wiki/...) — gestiamo entrambi i formati."""
    testo = cella.get_text(" ", strip=True)
    link = None
    a = cella.find("a")
    if a:
        href = a.get("href", "")
        if href.startswith("/wiki/"):
            link = BASE + href
        elif href.startswith("https://en.wikipedia.org/wiki/") or href.startswith("http://en.wikipedia.org/wiki/"):
            link = href.replace("http://", "https://", 1)
    return testo, link


def _tabella_espansa(tabella):
    """Converte una <table class="wikitable"> in DataFrame espandendo
    manualmente rowspan/colspan (es. sede/luogo condivisi tra eventi
    consecutivi nella stessa serata). Per ogni colonna intestazione
    viene aggiunta anche 'intestazione__link' con l'eventuale link
    Wikipedia della cella, cosi' i chiamanti possono recuperare il link
    dalla colonna che interessa (Name, Event, ...)."""
    trs = tabella.select("tr")
    intestazioni = [th.get_text(" ", strip=True) for th in trs[0].select("th")]
    n_col = len(intestazioni)

    righe_testo, righe_link = [], []
    pendenti = {}  # colonna -> (testo, link, righe_rimanenti)

    for tr in trs[1:]:
        celle = tr.find_all(["td", "th"], recursive=False)
        riga_testo, riga_link = [None] * n_col, [None] * n_col
        col, idx_cella = 0, 0

        while col < n_col:
            if col in pendenti:
                testo, link, rimanenti = pendenti[col]
                riga_testo[col], riga_link[col] = testo, link
                if rimanenti - 1 <= 0:
                    del pendenti[col]
                else:
                    pendenti[col] = (testo, link, rimanenti - 1)
                col += 1
                continue

            if idx_cella >= len(celle):
                col += 1
                continue
            c = celle[idx_cella]
            idx_cella += 1
            testo, link = _testo_e_link(c)
            span_r, span_c = _span(c, "rowspan"), _span(c, "colspan")

            for k in range(span_c):
                if col + k >= n_col:
                    break
                riga_testo[col + k], riga_link[col + k] = testo, link
                if span_r > 1:
                    pendenti[col + k] = (testo, link, span_r - 1)
            col += span_c

        righe_testo.append(riga_testo)
        righe_link.append(riga_link)

    df = pd.DataFrame(righe_testo, columns=intestazioni)
    df_link = pd.DataFrame(righe_link, columns=[f"{c}__link" for c in intestazioni])
    return pd.concat([df, df_link], axis=1)


RINOMINA_ROSTER = {
    "Name": "nome",
    "Age": "eta",
    "Ht.": "altezza",
    "Nickname": "soprannome",
    "Result / next fight / status": "risultato_recente",
    "Endeavor record": "record_endeavor",
    "MMA record": "record_mma",
}


def scarica_roster(usa_cache=True):
    """Roster attuale UFC per categoria di peso.
    Ritorna un DataFrame: categoria, nome, link, eta, altezza, soprannome,
    risultato_recente, record_endeavor, record_mma."""
    cache_file = CACHE_DIR / "roster.csv"
    if usa_cache and cache_file.exists():
        return pd.read_csv(cache_file)

    soup = _get_soup(ROSTER_URL)
    content = soup.select_one("#mw-content-text")

    tabelle_categorie = []
    categoria_corrente = None

    for el in content.find_all(["h2", "h3", "table"], recursive=True):
        if el.name in ("h2", "h3"):
            headline = el.select_one(".mw-headline") or el
            testo = headline.get_text(strip=True)
            if testo and testo.lower() not in ("see also", "notes", "references", "external links"):
                categoria_corrente = testo
            continue

        if "wikitable" not in (el.get("class") or []):
            continue

        intestazioni = [th.get_text(strip=True).lower() for th in el.select("tr")[0].select("th")]
        if not any("name" in h for h in intestazioni):
            continue

        df = _tabella_espansa(el)
        if "Name__link" in df.columns:
            df["link"] = df["Name__link"]
        df = df[[c for c in df.columns if not c.endswith("__link")]]
        df = df.rename(columns=RINOMINA_ROSTER)
        if "nome" not in df.columns:
            continue
        df["categoria"] = categoria_corrente
        tabelle_categorie.append(df)

    colonne = ["categoria", "nome", "link"] + list(RINOMINA_ROSTER.values())[1:]
    df = pd.concat(tabelle_categorie, ignore_index=True)
    df = df[[c for c in colonne if c in df.columns]]
    df = df.dropna(subset=["nome"]).reset_index(drop=True)

    df.to_csv(cache_file, index=False)
    return df


RINOMINA_EVENTI = {
    "Event": "evento",
    "Date": "data",
    "Venue": "sede",
    "Location": "luogo",
    "Attendance": "spettatori",
}


def scarica_eventi(usa_cache=True):
    """Eventi UFC programmati e passati.
    Ritorna un DataFrame: stato (programmato/passato), evento, link, data, sede, luogo, spettatori."""
    cache_file = CACHE_DIR / "eventi.csv"
    if usa_cache and cache_file.exists():
        return pd.read_csv(cache_file)

    soup = _get_soup(EVENTI_URL)
    content = soup.select_one("#mw-content-text")

    tabelle_stato = []
    sezione_corrente = None

    for el in content.find_all(["h2", "h3", "table"], recursive=True):
        if el.name in ("h2", "h3"):
            headline = el.select_one(".mw-headline") or el
            sezione_corrente = headline.get_text(strip=True)
            continue

        if "wikitable" not in (el.get("class") or []):
            continue

        intestazioni = [th.get_text(strip=True).lower() for th in el.select("tr")[0].select("th")]
        if not any("event" in h for h in intestazioni):
            continue

        stato = "programmato" if sezione_corrente and "scheduled" in sezione_corrente.lower() else "passato"

        df = _tabella_espansa(el)
        if "Event__link" in df.columns:
            df["link"] = df["Event__link"]
        df = df[[c for c in df.columns if not c.endswith("__link")]]
        df = df.rename(columns=RINOMINA_EVENTI)
        if "evento" not in df.columns:
            continue
        df["stato"] = stato
        tabelle_stato.append(df)

    colonne = ["stato", "evento", "link"] + [c for c in RINOMINA_EVENTI.values() if c != "evento"]
    df = pd.concat(tabelle_stato, ignore_index=True)
    df = df[[c for c in colonne if c in df.columns]]
    df = df.dropna(subset=["evento"]).reset_index(drop=True)

    df.to_csv(cache_file, index=False)
    return df


def scarica_dettaglio_lottatore(link, usa_cache=True):
    """Infobox + storico incontri di un singolo lottatore dalla sua pagina Wikipedia.
    Ritorna un dict con: nome, infobox (dict grezzo etichetta->valore),
    storico (DataFrame fight-by-fight se la tabella e' presente, altrimenti vuoto)."""
    slug = link.rstrip("/").split("/")[-1]
    cache_file = CACHE_DIR / f"lottatore_{slug}.csv"
    cache_storico = CACHE_DIR / f"storico_{slug}.csv"

    if usa_cache and cache_file.exists():
        infobox = pd.read_csv(cache_file).set_index("campo")["valore"].to_dict()
        storico = pd.read_csv(cache_storico) if cache_storico.exists() else pd.DataFrame()
        return {"nome": infobox.get("_nome"), "infobox": infobox, "storico": storico}

    soup = _get_soup(link)

    nome_tag = soup.select_one("#firstHeading")
    nome = nome_tag.get_text(strip=True) if nome_tag else slug

    infobox = {"_nome": nome}
    box = soup.select_one("table.infobox")
    if box:
        for tr in box.select("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td:
                campo = th.get_text(" ", strip=True)
                valore = td.get_text(" ", strip=True)
                if campo:
                    infobox[campo] = valore

    pd.DataFrame(
        [{"campo": k, "valore": v} for k, v in infobox.items()]
    ).to_csv(cache_file, index=False)

    storico = pd.DataFrame()
    for tabella in soup.select("table.wikitable"):
        intestazioni = [th.get_text(strip=True).lower() for th in tabella.select("tr")[0].select("th")]
        if any("res." in h or "opponent" in h for h in intestazioni):
            righe = []
            for tr in tabella.select("tr")[1:]:
                celle = tr.find_all(["td", "th"])
                if len(celle) < 3:
                    continue
                righe.append([c.get_text(" ", strip=True) for c in celle])
            if righe:
                n_col = len(intestazioni)
                righe = [r for r in righe if len(r) == n_col]
                storico = pd.DataFrame(righe, columns=intestazioni)
                break

    storico.to_csv(cache_storico, index=False)
    return {"nome": nome, "infobox": infobox, "storico": storico}


if __name__ == "__main__":
    print("Scarico roster...")
    roster = scarica_roster(usa_cache=False)
    print(f"{len(roster)} lottatori trovati, {roster['categoria'].nunique()} categorie")
    print(roster.head(10))

    print("\nScarico eventi...")
    eventi = scarica_eventi(usa_cache=False)
    print(f"{len(eventi)} eventi trovati")
    print(eventi.head(10))
