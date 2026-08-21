# FightItalia

Sito sugli sport da combattimento (MVP: UFC completo + KSW/Oktagon MMA
in Europa) — database lottatori, confronto "tale of the tape", card
eventi complete, con l'obiettivo di essere il primo prodotto interattivo
del genere in italiano (vedi ricerca fatta in chat: là fuori ci sono già
molti tool simili ma tutti in inglese).

## Perché Wikipedia e non UFCStats.com/Tapology/Sherdog

UFCStats.com (la fonte "standard" usata da quasi tutti gli scraper MMA su
GitHub/Kaggle) ha introdotto una verifica anti-bot con proof-of-work in
JavaScript. Tapology blocca le richieste automatiche con un 403. Sherdog
è accessibile ma non ha URL di organizzazione prevedibili/stabili.
Wikipedia espone gli stessi dati chiave (record, altezza, reach,
categoria di peso, storico incontri, calendario eventi, card completa
main/preliminary) in tabelle HTML stabili, senza protezioni
anti-scraping, a patto di usare uno User-Agent descrittivo (richiesto
dalla policy Wikimedia) — vedi `scraper_ufc.py`.

KSW e Oktagon MMA hanno anche loro una pagina Wikipedia "List of current
X fighters" strutturata come quella UFC, quindi hanno roster ed eventi
reali. Cage Warriors e ARES FC non ce l'hanno: per loro solo i campioni
attuali, curati a mano in `europa-data.js`.

## Architettura

Sito statico vero (HTML/CSS/JS scritti a mano, nessun framework/build
tool necessario) — Python serve solo a preparare i dati, non gira come
server. Prima versione era in Streamlit: aveva l'aria di una dashboard
interna, non di un sito per utenti veri, quindi è stata sostituita da
`docs/` (chiamata così, invece di `web/`, apposta: è il nome che GitHub
Pages riconosce senza bisogno di configurare nient'altro — vedi sotto).

```
scraper_ufc.py   scraping Wikipedia (roster, eventi, card, dettaglio lottatore) -> cache/*.csv
build_data.py    legge la cache e genera i JSON statici in docs/data/
docs/            il sito vero e proprio (index.html, confronto.html, eventi.html...)
```

## Come avviare in locale

```powershell
pip install -r requirements.txt
python build_data.py          # genera/aggiorna docs/data/ (~20-30 min la prima volta: 425 lottatori + 800 card eventi)
python -m http.server 8000 --directory docs
```

Si apre su `http://localhost:8000`. Rilanciare `build_data.py` ogni volta
che si vogliono dati aggiornati (salta tutto ciò che è già scaricato,
quindi le run successive sono quasi istantanee).

Per la sezione News serve una chiave Gemini gratuita (da
[Google AI Studio](https://aistudio.google.com/apikey)) in un file `.env`
nella root del progetto (`GEMINI_API_KEY=...`, gitignored):
```powershell
python build_news.py          # aggiorna docs/data/news.json — va rilanciato ogni 2-3 ore
```
Il piano gratuito ha un limite di richieste basso: lo script riprova con
backoff e, se il limite persiste, si ferma dopo al più 20 articoli nuovi
per run e riprende da dove aveva lasciato alla run successiva (gli
articoli già riscritti restano in cache, non vengono richiesti due volte).

Per rigenerare anche KSW/Oktagon (roster+eventi Europa):
```powershell
python -c "from build_data import genera_europa; genera_europa()"
```

## Pubblicare online

Sito statico puro: va bene qualsiasi hosting gratuito (Netlify, Vercel,
Cloudflare Pages, GitHub Pages). Con GitHub Pages:

1. In GitHub Desktop: **Publish repository** (repository **pubblico**,
   altrimenti GitHub Pages gratis non funziona).
2. Sul sito GitHub, nel repository: **Settings → Pages → Source: Deploy
   from a branch → Branch: master, cartella: /docs → Save**.
3. Dopo un minuto il sito è live su `https://<utente>.github.io/<repo>/`.

Per un dominio personalizzato (es. fightitalia.it): comprarlo da un
registrar (Register.it, Namecheap...), poi collegarlo nelle impostazioni
DNS del registrar + Settings → Pages → Custom domain sul repository.

## Cosa c'è

- **Database Lottatori**: roster UFC corrente per categoria di peso, più
  20 leggende ritirate aggiunte a mano (Khabib, Jon Jones, GSP, Anderson
  Silva...), con foto (dall'infobox Wikipedia) — filtro per categoria,
  filtro "Campioni" (attuali 🏆 ed ex 🥊) e ricerca per nome.
- **Confronto** (tale of the tape): scegli due lottatori (autocomplete,
  con foto), vedi record e statistiche affiancate, ultimi 5 incontri (con
  banner avversario/data al passaggio del mouse), storico incontri
  completo, grafici fisico/record, e se si sono già affrontati lo
  scontro diretto.
- **Eventi**: eventi UFC in ordine cronologico (più vicino per primo) con
  tag "Numerato"/"Fight Night" (per non confondere le due numerazioni
  indipendenti di UFC — es. "UFC 293" del 2023 e "UFC Fight Night 293"
  del 2026 sono due eventi diversi), ognuno con la propria scheda: card
  completa (main + preliminary + early preliminary) con risultati per
  gli eventi passati.
- **Europa**: KSW e Oktagon MMA hanno una pagina propria con due tab —
  Roster (lottatori reali, non solo campioni) ed Eventi (2025-2026) — dati
  veri da Wikipedia, non link esterni. Cage Warriors e ARES FC restano
  solo con l'elenco campioni (vedi sopra sul perché).
- **News**: ultimi articoli MMA/UFC da 4 feed RSS in inglese (BJPenn.com,
  MMA Mania, MMA Fighting, LowKick MMA — MMA Junkie escluso, il suo feed
  non è raggiungibile), riscritti da zero in italiano con Gemini (titolo +
  riassunto in 2-3 frasi, mai una traduzione letterale), con link diretto
  all'articolo originale e nome della fonte. `build_news.py` va rilanciato
  periodicamente (ogni 2-3 ore, non in tempo reale): ogni articolo viene
  riscritto una sola volta e tenuto in cache (`cache/news_cache.json`), un
  feed irraggiungibile viene saltato senza bloccare gli altri.
- **Schede di dettaglio proprie** (`lottatore.html`, `evento.html`): non
  si esce mai verso Wikipedia — per i lottatori UFC usiamo i dati già
  scaricati (inclusa la card completa per evento), per gli eventi UFC un
  riassunto testuale (con immagine) preso al volo dalla API pubblica REST
  di Wikipedia ma mostrato dentro una pagina nostra. Per KSW/Oktagon non
  c'è ancora una scheda di dettaglio per singolo lottatore/evento (solo
  la lista) — prossimo passo se serve.

I dati vengono scaricati una volta e messi in cache locale (cartella
`cache/`, non versionata). Foto, storico e card evento vengono
pre-scaricati da `build_data.py` (non on-demand): il sito finale è
completamente statico, nessun server Python in produzione.

## Un bug degno di nota (per chi tocca `scraper_ufc.py` in futuro)

`pandas` 3.0 ha introdotto un nuovo dtype `str` per le colonne testuali.
Una colonna con questo dtype che contiene anche un solo valore `None`
"dimentica" quel `None` e lo ritrasforma in `NaN` non appena la tocchi
con `.to_dict()` — anche dopo un `.where(pd.notna(df), None)` che
dovrebbe prevenirlo. Il risultato è un `NaN` non tra virgolette nel JSON
finale (non valido per lo standard JSON), che manda in crash silenzioso
`JSON.parse()` nel browser. Soluzione: `_record_puliti()` in
`scraper_ufc.py` ripulisce esplicitamente ogni valore con
`math.isnan()`, senza fidarsi del dtype. Usare quella funzione (o lo
stesso pattern) per qualsiasi nuovo scraper che restituisce dict con
colonne potenzialmente vuote.

## Roadmap (non ancora implementato)

1. **Roster completo per Cage Warriors e ARES FC** — nessuna pagina
   Wikipedia strutturata disponibile, servirebbe un'altra fonte (vedi
   sopra i limiti di Tapology/Sherdog).
2. **Card eventi per KSW/Oktagon** — tecnicamente fattibile (stessa
   tabella `toccolours` usata da UFC, verificato), richiede navigazione
   per ancora dentro le pagine-anno invece di una pagina evento dedicata.
3. **Boxe** via BoxRec (protetto da Cloudflare, più complesso) oppure una
   Boxing Data API a pagamento come scorciatoia.

## Nota sulla monetizzazione

In Italia la pubblicità di scommesse è vietata (Decreto Dignità, 2018).
Il modello di guadagno pensato per questo prodotto è quindi abbonamento
diretto per funzioni avanzate (non affiliazione con bookmaker) — modello
già validato all'estero da prodotti equivalenti in inglese (MMAPLAY365,
UFC Predictor, Blueprint MMA fanno pagare esattamente questo tipo di
analisi), più eventualmente pubblicità display e affiliazione DAZN
(streaming ufficiale UFC in Italia) una volta che c'è traffico reale.

## File

- `scraper_ufc.py` — scraping Wikipedia: roster UFC, roster
  organizzazioni europee, eventi, eventi organizzazioni europee, card
  evento, dettaglio lottatore (con foto). Cache su CSV locale.
- `build_data.py` — genera tutti i JSON in `docs/data/` a partire dalla
  cache: `roster.json`, `eventi.json`, un JSON per lottatore in
  `lottatori/`, un JSON per evento in `eventi/`, e per Europa
  `europa/{ksw,oktagon}-{roster,eventi}.json`.
- `build_news.py` — legge i 4 feed RSS, riscrive titolo e riassunto in
  italiano con Gemini (chiave in `.env`, variabile `GEMINI_API_KEY`) e
  genera `docs/data/news.json`. Cache su `cache/news_cache.json` (per
  articolo, non richiama Gemini due volte sullo stesso).
- `docs/` — il sito: `index.html` (database lottatori), `confronto.html`
  (tale of the tape), `eventi.html` (calendario), `europa.html`
  (organizzazioni europee), `organizzazione.html` (roster/eventi di una
  singola organizzazione europea), `lottatore.html`/`evento.html` (schede
  di dettaglio UFC), `news.html` (ultime notizie), `css/style.css`,
  `js/*.js` (vanilla JS, nessuna dipendenza esterna).
- `cache/` — CSV scaricati da Wikipedia, rigenerabile in qualsiasi
  momento (gitignored, serve solo in locale per velocizzare
  `build_data.py`).
- `docs/data/` — i JSON serviti dal sito, **versionati** (non
  gitignored): così il sito funziona subito anche pubblicato così com'è
  su un hosting statico, senza dover far girare Python in produzione.
  Vanno rigenerati e ricommittati quando si vogliono dati più freschi.
