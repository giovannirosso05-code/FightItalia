# MMA Hub

Sito MMA (MVP: solo UFC) — database lottatori, confronto "tale of the tape"
ed eventi, con l'obiettivo di essere il primo prodotto interattivo del
genere in italiano (vedi ricerca fatta in chat: là fuori ci sono già molti
tool simili ma tutti in inglese).

## Perché Wikipedia e non UFCStats.com

UFCStats.com (la fonte "standard" usata da quasi tutti gli scraper MMA su
GitHub/Kaggle) ha introdotto una verifica anti-bot con proof-of-work in
JavaScript. Scriverla per bypassarla sarebbe fragile e al limite dei
termini d'uso. Wikipedia espone gli stessi dati chiave (record, altezza,
reach, categoria di peso, storico incontri, calendario eventi) in tabelle
HTML stabili, senza protezioni anti-scraping, a patto di usare uno
User-Agent descrittivo (richiesto dalla policy Wikimedia) — vedi
`scraper_ufc.py`.

## Architettura

Sito statico vero (HTML/CSS/JS scritti a mano, nessun framework/build tool
necessario) — Python serve solo a preparare i dati, non gira come server.
Prima versione era in Streamlit: aveva l'aria di una dashboard interna,
non di un sito per utenti veri, quindi è stata sostituita da `docs/`
(chiamata cosí, invece di `web/`, apposta: è il nome che GitHub Pages
riconosce senza bisogno di configurare nient'altro — vedi sotto).

```
scraper_ufc.py   scraping Wikipedia (roster, eventi, dettaglio lottatore) -> cache/*.csv
build_data.py    legge la cache e genera i JSON statici in docs/data/
docs/            il sito vero e proprio (index.html, confronto.html, eventi.html...)
```

## Come avviare in locale

```powershell
pip install -r requirements.txt
python build_data.py          # genera/aggiorna docs/data/ (richiede qualche minuto la prima volta)
python -m http.server 8000 --directory docs
```

Si apre su `http://localhost:8000`. Rilanciare `build_data.py` ogni volta
che si vogliono dati aggiornati (salta i lottatori già scaricati, quindi
le run successive sono quasi istantanee).

## Pubblicare online (GitHub Pages, gratis)

1. In GitHub Desktop: **Publish repository** (crea il repository su GitHub
   e carica tutto in un click, usando l'account già collegato).
2. Sul sito GitHub, nel repository: **Settings → Pages → Source: Deploy
   from a branch → Branch: master, cartella: /docs → Save**.
3. Dopo un minuto il sito è live su
   `https://<tuo-utente>.github.io/Macinando/`.

Per aggiornare il sito pubblicato dopo una modifica: `git push` (o
"Push origin" in GitHub Desktop) — GitHub Pages si aggiorna da solo in
un minuto o due.

## Cosa c'è

- **Database Lottatori**: roster UFC corrente per categoria di peso, più
  20 leggende ritirate aggiunte a mano (Khabib, Jon Jones, GSP, Anderson
  Silva...) — filtro per categoria e ricerca per nome (684 lottatori
  all'ultimo scraping).
- **Confronto** (tale of the tape): scegli due lottatori (autocomplete),
  vedi record e statistiche affiancate, ultimi 5 incontri (con banner
  avversario/data al passaggio del mouse), storico incontri completo,
  grafici fisico/record, e se si sono già affrontati lo scontro diretto.
- **Eventi**: prossimi eventi UFC in ordine cronologico ed eventi recenti
  passati, con tag "Numerato"/"Fight Night" (per non confondere le due
  numerazioni indipendenti di UFC — es. "UFC 293" del 2023 e "UFC Fight
  Night 293" del 2026 sono due eventi diversi).
- **Europa**: le principali organizzazioni MMA europee (KSW, Oktagon MMA,
  Cage Warriors, ARES FC) — paese, anno di fondazione e campioni attuali
  per categoria di peso (dati curati a mano, non da scraping — vedi
  Roadmap).
- **Schede di dettaglio proprie** (`lottatore.html`, `evento.html`): non
  si esce mai verso Wikipedia — per i lottatori usiamo i dati già
  scaricati, per gli eventi un riassunto (con immagine) preso al volo
  dalla API pubblica REST di Wikipedia ma mostrato dentro una pagina
  nostra.

I dati vengono scaricati una volta e messi in cache locale (cartella
`cache/`, non versionata). Il dettaglio di ogni lottatore con pagina
Wikipedia viene pre-scaricato da `build_data.py` (non on-demand): il
sito finale è completamente statico, nessun server Python in produzione.

## Roadmap (non ancora implementato)

1. **Fase 2 — roster completo per le organizzazioni europee** (non solo i
   campioni, che ci sono già — vedi sopra). Tentato via Tapology: blocca
   le richieste automatiche con un 403 (a differenza di UFCStats/Wikipedia
   non è aggirabile in modo pulito). Sherdog è accessibile ma non ha URL
   di organizzazione prevedibili/stabili come UFCStats — richiede una
   ricerca caso per caso per ogni federazione, più lenta da costruire.
2. **Fase 3 — boxe** via BoxRec (protetto da Cloudflare, più complesso)
   oppure una Boxing Data API a pagamento come scorciatoia.

## Nota sulla monetizzazione

In Italia la pubblicità di scommesse è vietata (Decreto Dignità, 2018).
Il modello di guadagno pensato per questo prodotto è quindi abbonamento
diretto per funzioni avanzate (non affiliazione con bookmaker) — modello
già validato all'estero da prodotti equivalenti in inglese (MMAPLAY365,
UFC Predictor, Blueprint MMA fanno pagare esattamente questo tipo di
analisi).

## File

- `scraper_ufc.py` — scraping Wikipedia (roster, eventi, dettaglio
  lottatore) con cache su CSV locale.
- `build_data.py` — genera `docs/data/roster.json`, `docs/data/eventi.json`
  e un JSON per lottatore in `docs/data/lottatori/`.
- `docs/` — il sito: `index.html` (database lottatori), `confronto.html`
  (tale of the tape), `eventi.html` (calendario), `europa.html`
  (organizzazioni MMA europee), `lottatore.html`/`evento.html` (schede di
  dettaglio), `css/style.css`, `js/*.js` (vanilla JS, nessuna dipendenza
  esterna).
- `cache/` — CSV scaricati da Wikipedia, rigenerabile in qualsiasi momento
  (gitignored, serve solo in locale per velocizzare `build_data.py`).
- `docs/data/` — i JSON serviti dal sito, **versionati** (non gitignored):
  cosí il sito funziona subito anche se lo pubblichi cosí com'è su un
  hosting statico, senza dover far girare Python in produzione. Vanno
  rigenerati e ricommittati quando si vogliono dati più freschi.
