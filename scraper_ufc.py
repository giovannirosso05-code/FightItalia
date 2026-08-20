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

import math
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


def _record_puliti(records):
    """df.where(pd.notna(df), None).to_dict('records') NON basta con
    pandas 3.0: le colonne col nuovo dtype 'str' che contengono almeno un
    None lo silenziano di nuovo in NaN (bug/comportamento di dtype
    coercion), producendo un 'NaN' letterale nel JSON finale — non valido
    per JSON.parse() nel browser, che quindi fallisce in silenzio. Qui
    ripuliamo esplicitamente ogni valore, senza fidarci del dtype."""
    return [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
        for r in records
    ]


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
        # "redlink" = la pagina non esiste ancora su Wikipedia (link rosso,
        # porta al form di creazione articolo) — trattarlo come nessun
        # link, altrimenti lo slug derivato e' spazzatura tipo
        # "nome-action-edit-redlink-1".
        if link and "action=edit" in link:
            link = None
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
        img = box.select_one("img")
        if img and img.get("src"):
            src = img["src"]
            infobox["_immagine"] = "https:" + src if src.startswith("//") else src
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


def scarica_roster_organizzazione(url, nome_file_cache, usa_cache=True):
    """Roster corrente di un'organizzazione MMA diversa da UFC, per le
    poche che hanno una pagina Wikipedia "List of current X fighters"
    strutturata come quella UFC (KSW, Oktagon MMA — verificato; Cage
    Warriors e ARES FC NON ce l'hanno, vedi europa-data.js per quelle).
    A differenza di scarica_roster() non forziamo un mapping di colonne
    fisso: ogni organizzazione ha colonne leggermente diverse (es. KSW ha
    'KSW record' invece di 'Endeavor record', niente eta'/altezza), quindi
    teniamo i nomi colonna originali (in inglese) e lasciamo al chiamante
    scegliere cosa mostrare."""
    cache_file = CACHE_DIR / f"{nome_file_cache}.csv"
    if usa_cache and cache_file.exists():
        return pd.read_csv(cache_file)

    soup = _get_soup(url)
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
        if "Name" not in df.columns:
            continue
        # la colonna bandiera/nazionalita' spesso non ha intestazione
        # testuale (solo un'icona) e arriva qui come nome colonna vuoto.
        df.columns = [c if str(c).strip() else "Paese" for c in df.columns]
        df = df.rename(columns={"Name": "nome"})
        df["categoria"] = categoria_corrente
        tabelle_categorie.append(df)

    if not tabelle_categorie:
        return pd.DataFrame()

    df = pd.concat(tabelle_categorie, ignore_index=True)
    df = df.dropna(subset=["nome"])
    # una riga fantasma tipo "!a !a !a -9999..." (artefatto di ordinamento
    # della tabella, visto su KSW) non ha lettere vere nel nome — un
    # lottatore reale si' (il link Wikipedia invece puo' mancare
    # legittimamente se non ha ancora un articolo, li' teniamo la riga).
    df = df[df["nome"].str.contains(r"[A-Za-z]{2,}", regex=True, na=False)].reset_index(drop=True)
    df.to_csv(cache_file, index=False)
    return df


def scarica_eventi_organizzazione_anno(url, usa_cache=True):
    """Eventi di UN anno per un'organizzazione non-UFC (es. '2026 in
    Oktagon MMA', '2026 in Konfrontacja Sztuk Walki'). A differenza di UFC
    queste federazioni non hanno un'unica pagina con tutta la storia: e'
    una pagina per anno, e il nome dell'evento non linka a una pagina a
    se' ma a un'ancora (#Nome_Evento) nella STESSA pagina — quindi 'link'
    qui e' l'URL della pagina-anno con l'ancora, non una pagina dedicata."""
    slug = re.sub(r"[^a-z0-9]+", "-", url.rstrip("/").split("/")[-1].lower()).strip("-")
    cache_file = CACHE_DIR / f"eventi_{slug}.csv"
    if usa_cache and cache_file.exists():
        return pd.read_csv(cache_file)

    soup = _get_soup(url)
    content = soup.select_one("#mw-content-text")

    tabelle = []
    for el in content.select("table.wikitable"):
        intestazioni = [th.get_text(strip=True).lower() for th in el.select("tr")[0].select("th")]
        if not any("event" in h for h in intestazioni):
            continue
        df = _tabella_espansa(el)
        colonna_evento = next((c for c in df.columns if "event" in c.lower() and not c.endswith("__link")), None)
        if not colonna_evento:
            continue
        colonna_sede = next((c for c in df.columns if c.lower() in ("venue", "arena")), None)
        rinomina = {colonna_evento: "evento", "Date": "data", "Location": "luogo"}
        if colonna_sede:
            rinomina[colonna_sede] = "sede"
        if f"{colonna_evento}__link" in df.columns:
            df["link_ancora"] = df[f"{colonna_evento}__link"]
        df = df[[c for c in df.columns if not c.endswith("__link")]]
        df = df.rename(columns=rinomina)
        tabelle.append(df)

    if not tabelle:
        return pd.DataFrame()

    df = pd.concat(tabelle, ignore_index=True)
    df = df.dropna(subset=["evento"]).reset_index(drop=True)
    # gli anchor-link Wikipedia sono relativi ("#Nome") quando puntano alla
    # stessa pagina: costruiamo il link completo pagina+ancora a partire
    # dallo slug dell'evento (spazi -> underscore, come fa Wikipedia).
    df["link"] = url + "#" + df["evento"].str.replace(" ", "_", regex=False)
    df.to_csv(cache_file, index=False)
    return df


def scarica_card_evento(link, usa_cache=True):
    """Card di un evento (main + preliminary + eventuale early preliminary)
    dalla sua pagina Wikipedia individuale. La tabella (class="toccolours",
    NON "wikitable" — diversa dalle altre tabelle usate in questo file) ha
    righe-separatore a cella singola ("Main card (...)", "Preliminary card
    (...)") che segnano l'inizio di ogni sezione della card.
    Ritorna una lista di dict: sezione, categoria, fighter1, fighter1_link,
    fighter2, fighter2_link, metodo, round, tempo, note. Metodo/round/tempo
    sono vuoti per gli incontri non ancora disputati."""
    slug = link.rstrip("/").split("/")[-1]
    cache_file = CACHE_DIR / f"card_{slug}.csv"

    if usa_cache and cache_file.exists():
        df = pd.read_csv(cache_file)
        return _record_puliti(df.where(pd.notna(df), None).to_dict("records"))

    soup = _get_soup(link)
    tabella = None
    for t in soup.select("table.toccolours"):
        intestazioni_prime_righe = t.select("tr")[1].get_text(" ", strip=True).lower() if len(t.select("tr")) > 1 else ""
        if "weight class" in intestazioni_prime_righe:
            tabella = t
            break

    righe = []
    if tabella:
        sezione = None
        for tr in tabella.select("tr"):
            celle = tr.find_all(["td", "th"], recursive=False)
            testi = [c.get_text(" ", strip=True) for c in celle]

            if len(celle) == 1:
                etichetta = testi[0].lower()
                if "card" in etichetta:
                    sezione = testi[0]
                continue

            if not celle or testi[0].lower() == "weight class":
                continue
            if len(celle) < 4:
                continue

            f1_testo, f1_link = _testo_e_link(celle[1])
            f2_testo, f2_link = _testo_e_link(celle[3])
            righe.append({
                "sezione": sezione,
                "categoria": testi[0],
                "fighter1": f1_testo,
                "fighter1_link": f1_link,
                "fighter2": f2_testo,
                "fighter2_link": f2_link,
                "metodo": testi[4] if len(testi) > 4 else "",
                "round": testi[5] if len(testi) > 5 else "",
                "tempo": testi[6] if len(testi) > 6 else "",
                "note": testi[7] if len(testi) > 7 else "",
            })

    df = pd.DataFrame(righe)
    df.to_csv(cache_file, index=False)
    return _record_puliti(df.where(pd.notna(df), None).to_dict("records")) if not df.empty else []


if __name__ == "__main__":
    print("Scarico roster...")
    roster = scarica_roster(usa_cache=False)
    print(f"{len(roster)} lottatori trovati, {roster['categoria'].nunique()} categorie")
    print(roster.head(10))

    print("\nScarico eventi...")
    eventi = scarica_eventi(usa_cache=False)
    print(f"{len(eventi)} eventi trovati")
    print(eventi.head(10))
