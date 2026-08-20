"""
Script di controllo, SEPARATO dal sito live: confronta i dati salvati in
docs/data/lottatori/*.json con quelli attuali su Wikipedia, e segnala le
differenze in un report. Non modifica MAI il database automaticamente —
la decisione di aggiornare un campo resta manuale, dopo aver letto il
report.

Uso:
    python audit_dati.py                 # controlla tutti i lottatori
    python audit_dati.py --limite 20     # solo i primi 20 (per una prova rapida)

Il report va in audit_report.txt (cartella del progetto, non nel sito).
"""

import argparse
import json
import time
from pathlib import Path

from scraper_ufc import scarica_dettaglio_lottatore

CARTELLA_LOTTATORI = Path(__file__).parent / "docs" / "data" / "lottatori"
REPORT = Path(__file__).parent / "audit_report.txt"

# Solo i campi che ha senso confrontare: valori di fatto (altezza, reach...),
# non testo libero soggetto a piccole riformattazioni editoriali su Wikipedia.
CAMPI_DA_CONFRONTARE = [
    "Height", "Weight", "Reach", "Style", "Team", "Years active",
    "Wins", "Losses", "By knockout", "By submission", "By decision",
]


def confronta_lottatore(path_json):
    salvato = json.loads(path_json.read_text(encoding="utf-8"))
    link = salvato.get("link")
    if not link:
        return None

    try:
        fresco = scarica_dettaglio_lottatore(link, usa_cache=False)
    except Exception as e:
        return {"nome": salvato.get("nome", path_json.stem), "errore": str(e)}

    inf_salvato = salvato.get("infobox", {})
    inf_fresco = fresco.get("infobox", {})

    differenze = []
    for campo in CAMPI_DA_CONFRONTARE:
        v_salvato = inf_salvato.get(campo)
        v_fresco = inf_fresco.get(campo)
        if v_salvato != v_fresco and (v_salvato or v_fresco):
            differenze.append((campo, v_salvato, v_fresco))

    n_storico_salvato = len(salvato.get("storico") or [])
    n_storico_fresco = len(fresco["storico"]) if fresco.get("storico") is not None else 0
    if n_storico_salvato != n_storico_fresco:
        differenze.append(("Numero incontri nello storico", n_storico_salvato, n_storico_fresco))

    return {"nome": salvato.get("nome", path_json.stem), "differenze": differenze}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--pausa", type=float, default=0.3)
    args = parser.parse_args()

    file_lottatori = sorted(CARTELLA_LOTTATORI.glob("*.json"))
    if args.limite:
        file_lottatori = file_lottatori[: args.limite]

    righe_report = [
        f"Report di controllo dati — {len(file_lottatori)} lottatori confrontati con Wikipedia",
        "Nessuna modifica automatica: solo segnalazione. " + "=" * 40,
        "",
    ]
    con_differenze, con_errori = 0, 0

    for i, path_json in enumerate(file_lottatori):
        risultato = confronta_lottatore(path_json)
        if risultato is None:
            continue
        if "errore" in risultato:
            con_errori += 1
            righe_report.append(f"[ERRORE] {risultato['nome']}: {risultato['errore']}")
        elif risultato["differenze"]:
            con_differenze += 1
            righe_report.append(f"\n{risultato['nome']}:")
            for campo, attuale, wiki in risultato["differenze"]:
                righe_report.append(f"  - {campo}: attuale={attuale!r}  |  wikipedia={wiki!r}")

        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(file_lottatori)}] controllati, {con_differenze} con differenze finora")
        time.sleep(args.pausa)

    righe_report.insert(2, f"Lottatori con almeno una differenza: {con_differenze}. Errori: {con_errori}.\n")
    REPORT.write_text("\n".join(righe_report), encoding="utf-8")
    print(f"\nFatto. {con_differenze} lottatori con differenze, {con_errori} errori. Report in {REPORT}")


if __name__ == "__main__":
    main()
