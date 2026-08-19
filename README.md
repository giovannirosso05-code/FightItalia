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

## Come avviare

```powershell
pip install -r requirements.txt
python -m streamlit run app_streamlit.py
```

Si apre su `http://localhost:8501`.

## Cosa c'è nell'MVP

- **Database Lottatori**: roster UFC corrente per categoria di peso, con
  filtro e ricerca (664 lottatori all'ultimo scraping, ~660 con almeno
  età/altezza/record).
- **Confronto** (tale of the tape): scegli due lottatori, vedi statistiche
  affiancate, ultimi 5 incontri, grafici fisico/record, e se si sono già
  affrontati in passato lo storico dello scontro diretto.
- **Eventi**: prossimi eventi UFC programmati ed eventi recenti passati,
  con link alla pagina Wikipedia di ciascuno.

I dati vengono scaricati una volta e messi in cache locale (cartella
`cache/`, non versionata) — il bottone "Aggiorna dati" nella sidebar forza
un nuovo scraping. Il dettaglio di un lottatore (reach, storico incontri)
si scarica solo quando lo selezioni nel Confronto, non per tutti i 664 di
colpo.

## Roadmap (non ancora implementato)

1. **Fase 2 — altre organizzazioni MMA** (incluse quelle europee: KSW,
   Cage Warriors, Oktagon, ARES...) via Sherdog o Tapology, che coprono
   tutte le federazioni in un unico database invece di scrivere uno
   scraper diverso per ognuna.
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
- `app_streamlit.py` — l'interfaccia (3 tab: Database, Confronto, Eventi).
- `cache/` — CSV scaricati, rigenerabile in qualsiasi momento (gitignored).
