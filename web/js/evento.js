import { fetchJSON, renderChrome, icon, slugDaLink } from "./common.js";

renderChrome(null);

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

function dataEstesa(dataStr) {
  const d = new Date(dataStr);
  if (isNaN(d)) return dataStr || "";
  return `${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()}`;
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

  document.title = `${ev.evento} — MMA Hub`;
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
    </section>

    <div id="riassunto" style="max-width:640px; margin-bottom:50px;"></div>
  `;

  const riassuntoBox = document.getElementById("riassunto");
  const dati = ev.link ? await riassuntoWikipedia(ev.link) : null;

  if (dati && dati.extract) {
    riassuntoBox.innerHTML = `
      <div class="section-title" style="margin-top:0;">Riassunto</div>
      <div style="display:flex; gap:18px; align-items:flex-start;">
        ${dati.thumbnail ? `<img src="${dati.thumbnail.source}" alt="" style="width:120px; border-radius:var(--radius-sm); flex-shrink:0;">` : ""}
        <p style="color:var(--text-secondary); line-height:1.7;">${dati.extract}</p>
      </div>
      <p style="margin-top:14px; font-size:11.5px; color:var(--text-muted);">Riassunto automatico da Wikipedia (in inglese, fonte originale).</p>
    `;
  } else {
    riassuntoBox.innerHTML = `<div class="empty-state">Riassunto non disponibile per questo evento.</div>`;
  }
}

init();
