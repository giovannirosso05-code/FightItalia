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


def _nome_file_sicuro(testo):
    """Sostituisce con '_' i caratteri non ammessi nei nomi file su Windows
    (: \\ / * ? " < > |) piu' '#' — alcuni link Wikipedia (es. le pagine
    "The Ultimate Fighter ... Finale") hanno ':' nel titolo e '#ancora' per
    puntare a una sezione, e finivano dritti nel nome del file di cache
    causando OSError invalid argument."""
    return re.sub(r'[:\\/*?"<>|#]', "_", testo)


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


MESI_EN_IT = {
    "January": "gennaio", "February": "febbraio", "March": "marzo", "April": "aprile",
    "May": "maggio", "June": "giugno", "July": "luglio", "August": "agosto",
    "September": "settembre", "October": "ottobre", "November": "novembre", "December": "dicembre",
}
_MESI_PATTERN = "|".join(MESI_EN_IT.keys())
# "February 7, 1985 (age 41)" (mese-giorno-anno) o "15 May 1992 (age 34)"
# (giorno-mese-anno, l'altro formato usato da Wikipedia a seconda della
# pagina) — entrambi capitano, li normalizziamo allo stesso modo in output.
_DATA_MDY = re.compile(rf"\b({_MESI_PATTERN})\s+(\d{{1,2}}),\s+(\d{{4}})\s*\(\s*age\s+(\d+)\s*\)")
_DATA_DMY = re.compile(rf"\b(\d{{1,2}})\s+({_MESI_PATTERN})\s+(\d{{4}})\s*\(\s*age\s+(\d+)\s*\)")


def _pulisci_testo_wiki(testo):
    """Ripulisce artefatti comuni del text-scraping di Wikipedia:
    - citazioni tipo '[ 1 ]' (non sono dati, sono riferimenti a note)
    - la data ISO nascosta usata per il microformat hCard, es.
      '( 1985-02-07 )', pensata per essere invisibile via CSS ma che il
      semplice get_text() cattura come testo visibile
    - spazi doppi e spazi superflui dentro le parentesi lasciati dai due
      punti sopra."""
    if not isinstance(testo, str):
        return testo
    testo = re.sub(r"\(\s*\d{4}-\d{2}-\d{2}\s*\)", "", testo)
    testo = re.sub(r"\[\s*\d+\s*\]", "", testo)
    testo = re.sub(r"\(\s+", "(", testo)
    testo = re.sub(r"\s+\)", ")", testo)
    testo = re.sub(r"\s{2,}", " ", testo).strip()
    return testo


def _traduci_date_e_parole(testo):
    """Traduce in italiano le parti testuali inglesi piu' comuni nei campi
    anagrafici: 'February 7, 1985 (age 41)' -> '7 febbraio 1985 (41 anni)',
    'until 2022' -> 'fino al 2022', 'present' -> 'presente'."""
    def _sub_mdy(m):
        mese, giorno, anno, eta = m.groups()
        return f"{int(giorno)} {MESI_EN_IT[mese]} {anno} ({eta} anni)"

    def _sub_dmy(m):
        giorno, mese, anno, eta = m.groups()
        return f"{int(giorno)} {MESI_EN_IT[mese]} {anno} ({eta} anni)"

    testo = _DATA_MDY.sub(_sub_mdy, testo)
    testo = _DATA_DMY.sub(_sub_dmy, testo)
    testo = re.sub(r"\buntil\s+(\d{4})\b", r"fino al \1", testo)
    testo = re.sub(r"\bpresent\b", "presente", testo)
    return testo


def _swap_altezza_reach(testo):
    """'6 ft 3 in (191 cm)' -> '191 cm (6 ft 3 in)' — la richiesta e'
    mostrare prima l'unita' metrica, l'imperiale tra parentesi."""
    m = re.match(r"^(.+?)\s*\(([\d.]+\s*(?:cm|m))\)\s*(.*)$", testo)
    if not m:
        return testo
    imperiale, metrico, resto = m.groups()
    return f"{metrico} ({imperiale.strip()}){(' ' + resto) if resto else ''}"


def _swap_peso(testo):
    """'265 lb (120 kg; 18 st 13 lb)' -> '120 kg (265 lb)' — teniamo solo
    kg e lb (l'unita' 'stone' e' terziaria, non richiesta)."""
    m = re.match(r"^([\d.]+)\s*lb\s*\(\s*([\d.]+)\s*kg", testo)
    if not m:
        return testo
    lb, kg = m.groups()
    return f"{kg} kg ({lb} lb)"


def pulisci_campo_infobox(campo, valore):
    """Punto unico di pulizia per un valore infobox: rimuove citazioni/date
    ISO nascoste, traduce le parti testuali inglesi, e per altezza/peso/
    reach mette l'unita' metrica per prima. Usata sia dallo scraping
    (dati nuovi) sia dallo script di migrazione (dati gia' salvati)."""
    if not isinstance(valore, str) or campo.startswith("_"):
        return valore
    valore = _pulisci_testo_wiki(valore)
    valore = _traduci_date_e_parole(valore)
    if campo in ("Height", "Reach"):
        valore = _swap_altezza_reach(valore)
    elif campo == "Weight":
        valore = _swap_peso(valore)
    return valore


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
    if "altezza" in df.columns:
        df["altezza"] = df["altezza"].apply(lambda v: pulisci_campo_infobox("Height", v) if isinstance(v, str) else v)

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
    slug = _nome_file_sicuro(link.rstrip("/").split("/")[-1])
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
            # la thumbnail di default e' spesso larga solo 250px (sgranata se
            # ingrandita nella pagina lottatore) — prendiamo la versione 2x
            # dallo srcset se c'e', altrimenti raddoppiamo la larghezza
            # richiesta direttamente nell'URL (Wikipedia genera thumb di
            # qualsiasi dimensione su richiesta).
            match_2x = re.search(r"(\S+)\s+2x", img.get("srcset", ""))
            if match_2x:
                src = match_2x.group(1)
            else:
                src = re.sub(r"/(\d+)px-", lambda m: f"/{max(int(m.group(1)) * 2, 400)}px-", src)
            infobox["_immagine"] = "https:" + src if src.startswith("//") else src
        for tr in box.select("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td:
                campo = th.get_text(" ", strip=True)
                valore = td.get_text(" ", strip=True)
                if campo:
                    infobox[campo] = pulisci_campo_infobox(campo, valore)

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
    slug = _nome_file_sicuro(link.rstrip("/").split("/")[-1])
    cache_file = CACHE_DIR / f"card_{slug}.csv"

    if usa_cache and cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
        except pd.errors.EmptyDataError:
            # Card non ancora annunciata al momento dello scraping: la
            # cache di una lista vuota e' un CSV senza intestazione, che
            # read_csv non sa interpretare. E' un risultato valido (nessun
            # incontro), non un errore.
            return []
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


# Mappa sede -> fuso IANA, dedotta dal campo testuale "luogo" (citta',
# stato/provincia, paese) gia' presente nel database eventi. Serve perche'
# ufc.com NON mostra un orario assoluto affidabile: adatta il testo al fuso
# di chi naviga la pagina (verificato forzando fusi diversi via Chrome
# DevTools Protocol - stesso istante UTC, etichetta diversa ogni volta).
# Per interpretare correttamente l'orario mostrato dobbiamo quindi sapere
# GIA' il fuso reale della sede, e forzare il browser su quello prima di
# leggere la pagina (vedi scarica_orari_evento). Pattern degli stati/
# province USA/Canada PRIMA dei fallback generici "United States"/"Canada",
# altrimenti il generico vince sempre per primo match.
_FUSI_LUOGO = [
    (r"\bnevada\b", "America/Los_Angeles"),
    (r"\bcalifornia\b", "America/Los_Angeles"),
    (r"\bwashington\b", "America/Los_Angeles"),
    (r"\boregon\b", "America/Los_Angeles"),
    (r"\barizona\b", "America/Phoenix"),
    (r"\butah\b", "America/Denver"),
    (r"\bcolorado\b", "America/Denver"),
    (r"\btexas\b", "America/Chicago"),
    (r"\billinois\b", "America/Chicago"),
    (r"\bminnesota\b", "America/Chicago"),
    (r"\bwisconsin\b", "America/Chicago"),
    (r"\blouisiana\b", "America/Chicago"),
    (r"\bflorida\b", "America/New_York"),
    (r"new york", "America/New_York"),
    (r"new jersey", "America/New_York"),
    (r"\bmassachusetts\b", "America/New_York"),
    (r"\bohio\b", "America/New_York"),
    (r"\bmichigan\b", "America/New_York"),
    (r"\bgeorgia\b", "America/New_York"),
    (r"north carolina", "America/New_York"),
    (r"\balberta\b", "America/Edmonton"),
    (r"\bontario\b", "America/Toronto"),
    (r"\bquebec\b", "America/Toronto"),
    (r"british columbia", "America/Vancouver"),
    (r"\bmanitoba\b", "America/Winnipeg"),
    (r"united arab emirates|abu dhabi|\bdubai\b", "Asia/Dubai"),
    (r"saudi arabia|riyadh", "Asia/Riyadh"),
    (r"\bqatar\b|\bdoha\b", "Asia/Qatar"),
    (r"\bchina\b|shanghai|macau|macao|beijing", "Asia/Shanghai"),
    (r"singapore", "Asia/Singapore"),
    (r"\bjapan\b|tokyo|saitama", "Asia/Tokyo"),
    (r"south korea|seoul", "Asia/Seoul"),
    (r"philippines|manila", "Asia/Manila"),
    (r"\bfrance\b|\bparis\b", "Europe/Paris"),
    (r"germany|berlin|hamburg|cologne|dusseldorf", "Europe/Berlin"),
    (r"sweden|stockholm", "Europe/Stockholm"),
    (r"poland|gdansk|wroclaw|katowice|lodz|krakow|warsaw", "Europe/Warsaw"),
    (r"united kingdom|england|london|manchester|liverpool|\bwales\b|cardiff|scotland|glasgow", "Europe/London"),
    (r"ireland|dublin", "Europe/Dublin"),
    (r"\brussia\b|moscow", "Europe/Moscow"),
    (r"czech republic|prague", "Europe/Prague"),
    (r"denmark|copenhagen", "Europe/Copenhagen"),
    (r"brazil|rio de janeiro|sao paulo|são paulo|brasilia|goiania|belem|fortaleza|curitiba", "America/Sao_Paulo"),
    (r"\bmexico\b", "America/Mexico_City"),
    (r"argentina|buenos aires", "America/Argentina/Buenos_Aires"),
    (r"\bperth\b", "Australia/Perth"),
    (r"melbourne", "Australia/Melbourne"),
    (r"sydney|\bbrisbane\b", "Australia/Sydney"),
    (r"new zealand|auckland", "Pacific/Auckland"),
    (r"u\.s\.|united states", "America/New_York"),  # fallback generico USA: va DOPO gli stati specifici
    (r"\bcanada\b", "America/Toronto"),  # fallback generico Canada: va DOPO le province specifiche
]


def fuso_da_luogo(luogo):
    """Fuso IANA della sede, dedotto dal campo 'luogo' gia' presente nel
    database eventi (citta', stato/provincia, paese). Ritorna None se il
    luogo non e' riconosciuto: meglio non mostrare un orario che mostrarne
    uno sbagliato."""
    if not isinstance(luogo, str):
        return None
    luogo_low = luogo.lower()
    for pattern, fuso in _FUSI_LUOGO:
        if re.search(pattern, luogo_low):
            return fuso
    return None


def _slug_ufc_com(nome_evento):
    """Indovina lo slug della pagina evento su ufc.com dal nome che usiamo
    noi (preso da Wikipedia). Gli eventi numerati usano solo il numero
    ("UFC 333: Volkanovski vs. Evloev" -> "ufc-333"); i Fight Night usano i
    cognomi ("UFC Fight Night: Buckley vs. Malott" -> "ufc-fight-night-
    buckley-vs-malott"). I Fight Night ancora senza main event annunciato
    (es. "UFC Fight Night 293") non hanno una pagina su ufc.com: ritorna
    None, niente da indovinare."""
    m = re.match(r"^UFC (\d+)", nome_evento)
    if m:
        return f"ufc-{m.group(1)}"
    m = re.match(r"^UFC Fight Night:\s*(.+)$", nome_evento)
    if m:
        import unicodedata
        parte = unicodedata.normalize("NFKD", m.group(1)).encode("ascii", "ignore").decode("ascii").lower()
        parte = re.sub(r"[^a-z0-9]+", "-", parte).strip("-")
        return f"ufc-fight-night-{parte}" if parte else None
    return None


def _estrai_orari_da_testo(testo):
    """Cerca il blocco 'START TIMES' nel testo reso dalla pagina evento di
    ufc.com e ne estrae Early Prelims/Prelims/Main Card in formato 24h.
    Il testo va letto con il fuso del browser gia' forzato sulla sede
    (scarica_orari_evento), altrimenti gli orari sono nel fuso indovinato
    dal sito e non hanno alcun valore."""
    from datetime import datetime as _dt

    blocco = testo.split("START TIMES", 1)
    if len(blocco) < 2:
        return None
    corpo = blocco[1]
    mappa = {"Early Prelims": "early_prelims", "Prelims": "prelims", "Main Card": "main_card"}
    risultato = {"early_prelims": None, "prelims": None, "main_card": None}
    for etichetta, chiave in mappa.items():
        # "^...$" con MULTILINE: "Prelims" da solo non deve combaciare con
        # la riga "Early Prelims" (di cui e' una sottostringa finale).
        m = re.search(rf"^{re.escape(etichetta)}\s*$\n\s*(\d{{1,2}}:\d\d\s*[AP]M)", corpo, re.MULTILINE)
        if m:
            risultato[chiave] = _dt.strptime(re.sub(r"\s+", " ", m.group(1)), "%I:%M %p").strftime("%H:%M")
    return risultato if any(risultato.values()) else None


def scarica_orari_evento(nome_evento, luogo, usa_cache=True):
    """Orario di inizio (Early Prelims/Prelims/Main Card) della card,
    nel fuso REALE della sede — non nel fuso che ufc.com indovina per chi
    naviga (vedi commento su _FUSI_LUOGO). Richiede Selenium + Edge
    installato. Ritorna None se la sede non e' mappata, la pagina evento
    non esiste ancora su ufc.com, o il sito non e' raggiungibile: mai un
    orario indovinato o sbagliato."""
    fuso = fuso_da_luogo(luogo)
    slug = _slug_ufc_com(nome_evento)
    if not fuso or not slug:
        return None

    cache_file = CACHE_DIR / f"orari_{slug}.csv"
    if usa_cache and cache_file.exists():
        riga = pd.read_csv(cache_file).where(lambda d: pd.notna(d), None).iloc[0]
        return {
            "fuso_sede": riga["fuso_sede"],
            "early_prelims": riga["early_prelims"] or None,
            "prelims": riga["prelims"] or None,
            "main_card": riga["main_card"] or None,
        }

    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
        from selenium.webdriver.common.by import By
    except ImportError:
        return None
    import time as _time

    options = webdriver.EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")
    try:
        driver = webdriver.Edge(options=options)
    except WebDriverException:
        return None

    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": fuso})
        driver.get(f"https://www.ufc.com/event/{slug}")
        _time.sleep(5)
        testo = driver.find_element(By.TAG_NAME, "body").text
    except WebDriverException:
        return None
    finally:
        driver.quit()

    risultato = _estrai_orari_da_testo(testo)
    if not risultato:
        return None

    pd.DataFrame([{**risultato, "fuso_sede": fuso}]).to_csv(cache_file, index=False)
    return {**risultato, "fuso_sede": fuso}


if __name__ == "__main__":
    print("Scarico roster...")
    roster = scarica_roster(usa_cache=False)
    print(f"{len(roster)} lottatori trovati, {roster['categoria'].nunique()} categorie")
    print(roster.head(10))

    print("\nScarico eventi...")
    eventi = scarica_eventi(usa_cache=False)
    print(f"{len(eventi)} eventi trovati")
    print(eventi.head(10))
