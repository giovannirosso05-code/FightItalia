"""
MVP UFC: database lottatori, confronto (tale of the tape) ed eventi,
dati da Wikipedia (vedi scraper_ufc.py per la scelta della fonte).

Prossime fasi (non ancora in questo file): altre organizzazioni MMA
europee via Sherdog/Tapology, poi boxe via BoxRec.
"""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from scraper_ufc import scarica_dettaglio_lottatore, scarica_eventi, scarica_roster

st.set_page_config(page_title="MMA Hub", page_icon="🥊", layout="wide")

CATEGORIE_DIVISIONI = [
    "Heavyweights (265lb, 120 kg)",
    "Light heavyweights (205 lb, 93 kg)",
    "Middleweights (185 lb, 84 kg)",
    "Welterweights (170 lb, 77 kg)",
    "Lightweights (155 lb, 70 kg)",
    "Featherweights (145 lb, 65 kg)",
    "Bantamweights (135 lb, 61 kg)",
    "Flyweights (125 lb, 56 kg)",
    "Women's bantamweights (135 lb, 61 kg)",
    "Women's flyweights (125 lb, 56 kg)",
    "Women's strawweights (115 lb, 52 kg)",
]


@st.cache_data(show_spinner=False)
def carica_roster():
    return scarica_roster()


@st.cache_data(show_spinner=False)
def carica_eventi():
    return scarica_eventi()


@st.cache_data(show_spinner="Scarico i dati del lottatore da Wikipedia...")
def carica_dettaglio(link):
    return scarica_dettaglio_lottatore(link)


def _numero_da_record(record):
    """'28-14 (1 NC)' -> (28, 14). None se il formato non è riconosciuto."""
    if not isinstance(record, str):
        return None, None
    m = re.match(r"(\d+)[–-](\d+)", record.strip())
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def _cm_da_stringa(testo):
    """'6 ft 3 in (1.91 m)' -> 191.0. '79 in (201 cm) [1]' -> 201.0."""
    if not isinstance(testo, str):
        return None
    m = re.search(r"\(([\d.]+)\s*(cm|m)\)", testo)
    if not m:
        return None
    valore, unita = float(m.group(1)), m.group(2)
    return round(valore * 100 if unita == "m" else valore, 1)


def _forma_recente(storico, n=5):
    """Lista di ('Win'/'Loss'/..., avversario) per le ultime n voci dello storico."""
    if storico is None or storico.empty or "res." not in storico.columns:
        return []
    colonna_avversario = "opponent" if "opponent" in storico.columns else None
    righe = storico.head(n)
    out = []
    for _, r in righe.iterrows():
        avversario = r[colonna_avversario] if colonna_avversario else ""
        out.append((r["res."], avversario))
    return out


EMOJI_RISULTATO = {"win": "🟢", "loss": "🔴", "draw": "⚪", "nc": "⚫"}


def _badge_risultato(risultato):
    return EMOJI_RISULTATO.get(str(risultato).strip().lower(), "❔")


def _link_puliti(df):
    """LinkColumn mostra la scritta 'None' per le celle mancanti invece di
    lasciarle vuote: sostituiamo con stringa vuota prima di passare il
    DataFrame a st.dataframe."""
    df = df.copy()
    if "link" in df.columns:
        df["link"] = df["link"].fillna("")
    return df


def _testa_a_testa(storico, nome_avversario):
    """Cerca nello storico un incontro contro un avversario specifico (match parziale, case-insensitive)."""
    if storico is None or storico.empty or "opponent" not in storico.columns:
        return None
    match = storico[storico["opponent"].str.contains(re.escape(nome_avversario), case=False, na=False)]
    return match.iloc[0] if not match.empty else None


st.title("🥊 MMA Hub")
st.caption(
    "MVP — dati UFC da Wikipedia. Prossime fasi: organizzazioni MMA europee "
    "(Sherdog/Tapology) e boxe (BoxRec)."
)

tab_db, tab_confronto, tab_eventi = st.tabs(["📋 Database Lottatori", "⚖️ Confronto", "📅 Eventi"])

# ----------------------------------------------------------------------------
# TAB 1: Database Lottatori
# ----------------------------------------------------------------------------
with tab_db:
    roster = carica_roster()

    col_filtro, col_ricerca = st.columns([2, 1])
    with col_filtro:
        categorie_disponibili = sorted(roster["categoria"].dropna().unique().tolist())
        default_sel = [c for c in categorie_disponibili if c in CATEGORIE_DIVISIONI]
        categorie_scelte = st.multiselect(
            "Categoria di peso", categorie_disponibili, default=default_sel or categorie_disponibili
        )
    with col_ricerca:
        ricerca = st.text_input("Cerca lottatore", placeholder="es. Makhachev")

    df_vista = roster[roster["categoria"].isin(categorie_scelte)] if categorie_scelte else roster
    if ricerca:
        df_vista = df_vista[df_vista["nome"].str.contains(ricerca, case=False, na=False)]

    st.caption(f"{len(df_vista)} lottatori")

    colonne_vista = ["nome", "categoria", "eta", "altezza", "soprannome", "record_mma", "risultato_recente", "link"]
    colonne_vista = [c for c in colonne_vista if c in df_vista.columns]

    st.dataframe(
        _link_puliti(df_vista[colonne_vista]),
        column_config={
            "nome": "Nome",
            "categoria": "Categoria",
            "eta": st.column_config.NumberColumn("Età"),
            "altezza": "Altezza",
            "soprannome": "Soprannome",
            "record_mma": "Record MMA",
            "risultato_recente": "Ultimo risultato / prossimo incontro",
            "link": st.column_config.LinkColumn("Wikipedia", display_text="apri"),
        },
        hide_index=True,
        use_container_width=True,
        height=600,
    )

# ----------------------------------------------------------------------------
# TAB 2: Confronto (Tale of the Tape)
# ----------------------------------------------------------------------------
with tab_confronto:
    roster = carica_roster()
    roster_con_pagina = roster.dropna(subset=["link"]).reset_index(drop=True)

    opzioni = (roster_con_pagina["nome"] + "  —  " + roster_con_pagina["categoria"].fillna("")).tolist()

    indici_divisioni_reali = [
        i for i, cat in enumerate(roster_con_pagina["categoria"]) if cat in CATEGORIE_DIVISIONI
    ]
    default_a = indici_divisioni_reali[0] if indici_divisioni_reali else 0
    default_b = indici_divisioni_reali[1] if len(indici_divisioni_reali) > 1 else min(default_a + 1, len(opzioni) - 1)

    col_a, col_b = st.columns(2)
    with col_a:
        scelta_a = st.selectbox("Lottatore A", opzioni, index=default_a if opzioni else None, key="lottatore_a")
    with col_b:
        scelta_b = st.selectbox("Lottatore B", opzioni, index=default_b if opzioni else None, key="lottatore_b")

    if not opzioni:
        st.warning("Nessun lottatore con pagina Wikipedia disponibile nel roster caricato.")
    elif scelta_a == scelta_b:
        st.info("Scegli due lottatori diversi per confrontarli.")
    else:
        riga_a = roster_con_pagina.iloc[opzioni.index(scelta_a)]
        riga_b = roster_con_pagina.iloc[opzioni.index(scelta_b)]

        dettaglio_a = carica_dettaglio(riga_a["link"])
        dettaglio_b = carica_dettaglio(riga_b["link"])

        col_a, col_vs, col_b = st.columns([5, 1, 5])

        for col, riga, dettaglio in [(col_a, riga_a, dettaglio_a), (col_b, riga_b, dettaglio_b)]:
            with col:
                st.subheader(dettaglio["nome"])
                infobox = dettaglio["infobox"]
                st.markdown(f"**Categoria:** {infobox.get('Division', riga.get('categoria', '—'))}")
                st.markdown(f"**Altezza:** {infobox.get('Height', riga.get('altezza', '—'))}")
                st.markdown(f"**Reach:** {infobox.get('Reach', '—')}")
                st.markdown(f"**Team:** {infobox.get('Team', '—')}")
                st.markdown(f"**Attivo dal:** {infobox.get('Years active', '—')}")

                forma = _forma_recente(dettaglio["storico"])
                if forma:
                    badges = "  ".join(_badge_risultato(r) for r, _ in forma)
                    st.markdown(f"**Ultimi {len(forma)} incontri:** {badges}")
                    with st.expander("Dettaglio ultimi incontri"):
                        for risultato, avversario in forma:
                            st.write(f"{_badge_risultato(risultato)} {risultato} vs {avversario}")

        with col_vs:
            st.markdown("<h2 style='text-align:center; margin-top:2rem;'>VS</h2>", unsafe_allow_html=True)

        st.divider()

        vinte_a, perse_a = _numero_da_record(riga_a.get("record_mma"))
        vinte_b, perse_b = _numero_da_record(riga_b.get("record_mma"))
        altezza_a = _cm_da_stringa(dettaglio_a["infobox"].get("Height"))
        altezza_b = _cm_da_stringa(dettaglio_b["infobox"].get("Height"))
        reach_a = _cm_da_stringa(dettaglio_a["infobox"].get("Reach"))
        reach_b = _cm_da_stringa(dettaglio_b["infobox"].get("Reach"))

        st.markdown("**Tale of the Tape**")
        col_fisico, col_record = st.columns(2)

        def _grafico_confronto(titolo, metriche, valori_a, valori_b):
            fig = go.Figure()
            fig.add_trace(go.Bar(name=dettaglio_a["nome"], y=metriche, x=valori_a, orientation="h"))
            fig.add_trace(go.Bar(name=dettaglio_b["nome"], y=metriche, x=valori_b, orientation="h"))
            fig.update_layout(
                barmode="group",
                title=titolo,
                height=260,
                margin=dict(l=10, r=10, t=40, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            return fig

        with col_fisico:
            st.plotly_chart(
                _grafico_confronto(
                    "Fisico (cm)", ["Reach", "Altezza"], [reach_a, altezza_a], [reach_b, altezza_b]
                ),
                use_container_width=True,
            )
        with col_record:
            st.plotly_chart(
                _grafico_confronto(
                    "Record MMA", ["Sconfitte", "Vittorie"], [perse_a, vinte_a], [perse_b, vinte_b]
                ),
                use_container_width=True,
            )

        scontro_diretto = _testa_a_testa(dettaglio_a["storico"], dettaglio_b["nome"])
        if scontro_diretto is not None:
            st.success(
                f"Si sono già affrontati: **{scontro_diretto['res.']}** per {dettaglio_a['nome']} "
                f"({scontro_diretto.get('method', '—')}, {scontro_diretto.get('event', '—')}, "
                f"{scontro_diretto.get('date', '—')})"
            )
        else:
            st.caption("Non risultano incontri diretti precedenti tra questi due lottatori.")

# ----------------------------------------------------------------------------
# TAB 3: Eventi
# ----------------------------------------------------------------------------
with tab_eventi:
    eventi = carica_eventi()

    st.subheader("Prossimi eventi")
    prossimi = eventi[eventi["stato"] == "programmato"].copy()
    if prossimi.empty:
        st.info("Nessun evento programmato trovato.")
    else:
        colonne = [c for c in ["evento", "data", "sede", "luogo", "link"] if c in prossimi.columns]
        st.dataframe(
            _link_puliti(prossimi[colonne]),
            column_config={
                "evento": "Evento",
                "data": "Data",
                "sede": "Sede",
                "luogo": "Luogo",
                "link": st.column_config.LinkColumn("Wikipedia", display_text="apri"),
            },
            hide_index=True,
            use_container_width=True,
        )
    st.caption("In Italia gli eventi UFC si seguono in streaming legale su DAZN.")

    st.subheader("Eventi recenti")
    passati = eventi[eventi["stato"] == "passato"].copy()
    n_mostra = st.slider("Quanti eventi passati mostrare", 5, 100, 20)
    colonne_passati = [c for c in ["evento", "data", "sede", "luogo", "spettatori", "link"] if c in passati.columns]
    st.dataframe(
        _link_puliti(passati[colonne_passati].head(n_mostra)),
        column_config={
            "evento": "Evento",
            "data": "Data",
            "sede": "Sede",
            "luogo": "Luogo",
            "spettatori": "Spettatori",
            "link": st.column_config.LinkColumn("Wikipedia", display_text="apri"),
        },
        hide_index=True,
        use_container_width=True,
    )

with st.sidebar:
    st.header("⚙️ Dati")
    st.caption("Roster ed eventi sono in cache locale dopo il primo caricamento.")
    if st.button("🔄 Aggiorna dati da Wikipedia"):
        scarica_roster(usa_cache=False)
        scarica_eventi(usa_cache=False)
        st.cache_data.clear()
        st.success("Dati aggiornati.")
        st.rerun()
