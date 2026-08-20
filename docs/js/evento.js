import { fetchJSON, renderChrome, icon, slugDaLink, classeRisultato } from "./common.js";

renderChrome(null);

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

function dataEstesa(dataStr) {
  const d = new Date(dataStr);
  if (isNaN(d)) return dataStr || "";
  return `${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()}`;
}

const ETICHETTE_ORARI = { early_prelims: "Early Prelims", prelims: "Prelims", main_card: "Main Card" };

function rigaOrario(etichetta, o) {
  if (!o) return "";
  const italia = o.giorno_dopo ? `${o.italia} (giorno dopo)` : o.italia;
  return `<div class="row"><span class="k">${etichetta}</span><span class="v">${o.locale} sede — ${italia} Italia</span></div>`;
}

function blocoOrari(orari) {
  if (!orari) return "";
  const righe = Object.entries(ETICHETTE_ORARI)
    .map(([chiave, etichetta]) => rigaOrario(etichetta, orari[chiave]))
    .join("");
  if (!righe) return "";
  return `
    <div style="margin-top:20px; max-width:420px;">
      <div class="section-title" style="margin-top:0;">Orario di inizio</div>
      <div class="compare-col a">${righe}</div>
      <p style="margin-top:8px; font-size:11.5px; color:var(--text-muted);">
        Fuso sede: ${orari.fuso_sede}. Orario Italia calcolato automaticamente (cambio ora legale incluso). Fonte: ufc.com.
      </p>
    </div>`;
}

function tagTipo(tipo) {
  if (tipo === "Numerato") return `<span class="tag numerato">Numerato</span>`;
  if (tipo === "Fight Night") return `<span class="tag fight-night">Fight Night</span>`;
  return "";
}

async function riassuntoWikipedia(link) {
  // Non abbiamo scaricato il testo di tutti gli 806 eventi in fase di
  // build (troppo pesante) — qui, solo quando l'utente apre la scheda di
  // QUESTO singolo evento, chiediamo un riassunto alla API pubblica REST
  // di Wikipedia (supporta CORS, pensata apposta per essere richiamata da
  // pagine come questa) cosi' il contenuto resta dentro la nostra pagina
  // invece di mandare l'utente via.
  const titolo = link.split("/wiki/")[1];
  if (!titolo) return null;
  try {
    const res = await fetch(`https://en.wikipedia.org/api/rest_v1/page/summary/${titolo}`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function nomeConLink(nome, link) {
  if (!nome) return "—";
  const slug = link ? slugDaLink(link) : null;
  return slug ? `<a href="lottatore.html?slug=${slug}">${nome}</a>` : nome;
}

// Confronto rapido dentro la card del match: solo se ENTRAMBI i lottatori
// sono nel nostro database (il roster copre solo UFC attuale + leggende,
// molti nomi di prelim/undercard non ci sono — in quel caso si mostrano
// solo i nomi, senza dati, invece di un blocco vuoto).
function confrontoRapidoBout(rigaA, rigaB) {
  if (!rigaA || !rigaB) return "";
  const eta = rigaA.eta && rigaB.eta ? `${rigaA.eta} — ${rigaB.eta} anni` : null;
  return `
    <div class="bout-confronto">
      <span>${rigaA.record_mma || "—"}</span>
      <span class="k">Record</span>
      <span>${rigaB.record_mma || "—"}</span>
      ${eta ? `<span>${rigaA.eta}</span><span class="k">Età</span><span>${rigaB.eta}</span>` : ""}
      <a href="confronto.html?a=${rigaA.slug}&b=${rigaB.slug}" class="bout-confronto-link">Confronta →</a>
    </div>`;
}

function rigaIncontro(b, roster) {
  const haRisultato = b.metodo && b.metodo.trim();
  const slugA = b.fighter1_link ? slugDaLink(b.fighter1_link) : null;
  const slugB = b.fighter2_link ? slugDaLink(b.fighter2_link) : null;
  const rigaA = slugA ? roster.find((r) => r.slug === slugA) : null;
  const rigaB = slugB ? roster.find((r) => r.slug === slugB) : null;
  return `
    <div class="bout-row">
      <span class="tag bout-cat">${b.categoria || ""}</span>
      <div class="bout-main">
        <div class="bout-fighters">
          <span class="${haRisultato ? "bout-winner" : ""}">${nomeConLink(b.fighter1, b.fighter1_link)}</span>
          <span class="bout-vs">vs</span>
          <span>${nomeConLink(b.fighter2, b.fighter2_link)}</span>
        </div>
        ${haRisultato ? `<div class="bout-result">${b.metodo} · Round ${b.round} · ${b.tempo}</div>` : confrontoRapidoBout(rigaA, rigaB)}
      </div>
    </div>`;
}

function sezioneCard(titolo, incontri, roster) {
  if (!incontri.length) return "";
  return `
    <div class="event-group-title">${titolo}</div>
    <div class="bout-list">${incontri.map((b) => rigaIncontro(b, roster)).join("")}</div>`;
}

async function caricaCard(link) {
  const slug = slugDaLink(link);
  try {
    return await fetchJSON(`data/eventi/${slug}.json`);
  } catch {
    return [];
  }
}

async function init() {
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug");
  const out = document.getElementById("scheda-evento");

  if (!slug) {
    out.innerHTML = `<div class="empty-state">Evento non specificato. <a href="eventi.html">Torna al calendario</a>.</div>`;
    return;
  }

  const eventi = await fetchJSON("data/eventi.json");
  const ev = eventi.find((e) => slugDaLink(e.link) === slug);

  if (!ev) {
    out.innerHTML = `<div class="empty-state">Evento non trovato. <a href="eventi.html">Torna al calendario</a>.</div>`;
    return;
  }

  document.title = `${ev.evento} — FightItalia`;
  const luogo = [ev.sede, ev.luogo].filter(Boolean).join(", ");

  out.innerHTML = `
    <section class="hero" style="padding:44px 0 24px; border-bottom:none;">
      <h1 style="font-size:clamp(26px,4vw,40px);">${ev.evento}</h1>
      <div style="margin-top:10px; display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        ${tagTipo(ev.tipo)}
        <span style="color:var(--text-secondary); font-size:14px;">${dataEstesa(ev.data)}</span>
      </div>
      ${luogo ? `<p style="margin-top:14px; color:var(--text-secondary); display:flex; align-items:center; gap:6px;">${icon("pin")} ${luogo}</p>` : ""}
      ${ev.spettatori ? `<p style="margin-top:6px; color:var(--text-muted); font-size:13px;">Spettatori: ${ev.spettatori}</p>` : ""}
      ${blocoOrari(ev.orari)}
    </section>

    <div id="card-evento" style="max-width:720px;"><div class="empty-state">Carico la card...</div></div>
    <div id="riassunto" style="max-width:640px; margin-bottom:50px;"></div>
  `;

  const cardBox = document.getElementById("card-evento");
  const [card, roster] = ev.link
    ? await Promise.all([caricaCard(ev.link), fetchJSON("data/roster.json").catch(() => [])])
    : [[], []];

  if (card.length) {
    const main = card.filter((b) => (b.sezione || "").toLowerCase().startsWith("main"));
    const prelim = card.filter((b) => (b.sezione || "").toLowerCase().startsWith("preliminary"));
    const early = card.filter((b) => (b.sezione || "").toLowerCase().startsWith("early"));
    cardBox.innerHTML = sezioneCard("Main Card", main, roster) + sezioneCard("Preliminary Card", prelim, roster) + sezioneCard("Early Preliminary Card", early, roster);
  } else {
    cardBox.innerHTML = `<div class="empty-state">Card non ancora disponibile per questo evento.</div>`;
  }

  const riassuntoBox = document.getElementById("riassunto");
  const dati = ev.link ? await riassuntoWikipedia(ev.link) : null;

  if (dati && dati.extract) {
    riassuntoBox.innerHTML = `
      <div class="section-title">Riassunto</div>
      <div style="display:flex; gap:18px; align-items:flex-start;">
        ${dati.thumbnail ? `<img src="${dati.thumbnail.source}" alt="" style="width:120px; border-radius:var(--radius-sm); flex-shrink:0;">` : ""}
        <p style="color:var(--text-secondary); line-height:1.7;">${dati.extract}</p>
      </div>
      <p style="margin-top:14px; font-size:11.5px; color:var(--text-muted);">Riassunto automatico da Wikipedia (in inglese, fonte originale).</p>
    `;
  } else {
    riassuntoBox.innerHTML = "";
  }
}

init();
