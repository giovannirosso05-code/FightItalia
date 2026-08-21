import { fetchJSON, renderChrome, icon } from "./common.js";

renderChrome("news");

function tempoFa(dataIso) {
  if (!dataIso) return "";
  const diffMs = Date.now() - new Date(dataIso).getTime();
  const minuti = Math.floor(diffMs / 60000);
  if (minuti < 60) return `${Math.max(minuti, 0)} min fa`;
  const ore = Math.floor(minuti / 60);
  if (ore < 24) return `${ore} ${ore === 1 ? "ora" : "ore"} fa`;
  const giorni = Math.floor(ore / 24);
  return `${giorni} ${giorni === 1 ? "giorno" : "giorni"} fa`;
}

function cardNews(articolo) {
  return `
    <article class="news-card">
      <div class="news-meta">
        <span class="news-fonte">${articolo.fonte}</span>
        <span class="news-tempo">${tempoFa(articolo.pubblicato)}</span>
      </div>
      <h2 class="news-titolo">${articolo.titolo}</h2>
      <p class="news-riassunto">${articolo.riassunto}</p>
      <a class="news-link" href="${articolo.url}" target="_blank" rel="noopener noreferrer">
        ${icon("link")} Leggi su ${articolo.fonte}
      </a>
    </article>`;
}

async function init() {
  const grid = document.getElementById("news-grid");
  try {
    const dati = await fetchJSON("data/news.json");
    const articoli = dati.articoli || [];
    grid.innerHTML =
      articoli.map(cardNews).join("") ||
      `<div class="empty-state">Nessuna news disponibile al momento.</div>`;
    if (dati.generato_il) {
      const d = new Date(dati.generato_il);
      document.getElementById("news-aggiornamento").textContent =
        `Aggiornato ${d.toLocaleDateString("it-IT")} alle ${d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}`;
    }
  } catch (errore) {
    grid.innerHTML = `<div class="empty-state">Impossibile caricare le news al momento.</div>`;
  }
}

init();
