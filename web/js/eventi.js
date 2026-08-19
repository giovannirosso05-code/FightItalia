import { fetchJSON, renderChrome, icon, slugDaLink } from "./common.js";

renderChrome("eventi");

const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

function blocchettoData(dataStr) {
  const d = new Date(dataStr);
  if (isNaN(d)) return `<div class="event-date"><span class="day">?</span></div>`;
  return `<div class="event-date"><span class="day">${d.getDate()}</span><span class="month">${MESI[d.getMonth()]} ${d.getFullYear()}</span></div>`;
}

function tagTipo(tipo) {
  if (tipo === "Numerato") return `<span class="tag numerato">Numerato</span>`;
  if (tipo === "Fight Night") return `<span class="tag fight-night">Fight Night</span>`;
  return "";
}

function rigaEvento(ev) {
  const luogo = [ev.sede, ev.luogo].filter(Boolean).join(" — ");
  return `
    <div class="event-row">
      ${blocchettoData(ev.data)}
      <div class="event-main">
        <div class="name">${ev.evento} ${tagTipo(ev.tipo)}</div>
        ${luogo ? `<div class="venue">${icon("pin")} ${luogo}</div>` : ""}
      </div>
      ${ev.link ? `<a class="event-link" href="evento.html?slug=${slugDaLink(ev.link)}">Dettagli →</a>` : "<span></span>"}
    </div>`;
}

function ordinaData(lista, crescente) {
  return [...lista].sort((x, y) => {
    const dx = new Date(x.data), dy = new Date(y.data);
    return crescente ? dx - dy : dy - dx;
  });
}

let passati = [];
let mostrati = 15;

function renderPassati() {
  document.getElementById("eventi-passati").innerHTML = passati.slice(0, mostrati).map(rigaEvento).join("");
  document.getElementById("passati-count").textContent = `(${passati.length})`;
  document.getElementById("load-more").style.display = mostrati >= passati.length ? "none" : "block";
}

async function init() {
  const eventi = await fetchJSON("data/eventi.json");
  // Ordine cronologico crescente: il prossimo evento (il più vicino da
  // oggi) va per primo, non il più lontano nel tempo.
  const prossimi = ordinaData(eventi.filter((e) => e.stato === "programmato"), true);
  passati = ordinaData(eventi.filter((e) => e.stato === "passato"), false);

  document.getElementById("eventi-prossimi").innerHTML =
    prossimi.map(rigaEvento).join("") || `<div class="empty-state">Nessun evento programmato trovato.</div>`;
  renderPassati();
  document.getElementById("load-more").addEventListener("click", () => {
    mostrati += 20;
    renderPassati();
  });
}

init();
