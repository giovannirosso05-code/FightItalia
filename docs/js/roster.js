import { fetchJSON, renderChrome, icon, debounce } from "./common.js";

renderChrome("database");
document.getElementById("search-icon").innerHTML = icon("search");

const ORDINE_CATEGORIE = [
  "Leggende (ex campioni)",
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
];

let roster = [];
let categoriaAttiva = null;

function nomeBreveCategoria(cat) {
  if (!cat) return "—";
  return cat.replace(/\s*\([^)]*\)/, "");
}

function renderStatStrip() {
  const categorie = new Set(roster.map((r) => r.categoria).filter((c) => ORDINE_CATEGORIE.includes(c)));
  document.getElementById("stat-strip").innerHTML = `
    <div class="stat"><div class="value">${roster.length}</div><div class="label">Lottatori</div></div>
    <div class="stat"><div class="value">${categorie.size}</div><div class="label">Categorie di peso</div></div>
    <div class="stat"><div class="value">Wikipedia</div><div class="label">Fonte dati</div></div>
  `;
}

const FILTRO_CAMPIONI = "__CAMPIONI__";

function renderPills() {
  const presenti = ORDINE_CATEGORIE.filter((c) => roster.some((r) => r.categoria === c));
  const cont = document.getElementById("category-pills");
  const pillCampioni = `<button class="pill" data-cat="${FILTRO_CAMPIONI}">🏆 Campioni (attuali ed ex)</button>`;
  cont.innerHTML = pillCampioni + presenti.map((c) => `<button class="pill" data-cat="${c}">${nomeBreveCategoria(c)}</button>`).join("");
  cont.querySelectorAll(".pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      const cat = btn.dataset.cat;
      categoriaAttiva = categoriaAttiva === cat ? null : cat;
      cont.querySelectorAll(".pill").forEach((b) => b.classList.toggle("active", b.dataset.cat === categoriaAttiva));
      renderGrid();
    });
  });
}

function cardLottatore(r) {
  const eta = r.eta ? `<span>${icon("age")} ${r.eta} anni</span>` : "";
  const altezza = r.altezza ? `<span>${icon("ruler")} ${r.altezza}</span>` : "";
  const href = r.slug ? `lottatore.html?slug=${r.slug}` : null;
  const nome = href ? `<a href="${href}">${r.nome}</a>` : r.nome;
  const link = href ? `<a href="${href}">${icon("link")}</a>` : "";
  const corona = r.campione_attuale ? " 🏆" : r.ex_campione ? " 🥊" : "";
  return `
    <div class="fighter-card">
      <div class="top-row">
        <div>
          <div class="name">${nome}${corona}</div>
          ${r.soprannome ? `<div class="nickname">"${r.soprannome}"</div>` : ""}
        </div>
        <span class="tag">${nomeBreveCategoria(r.categoria)}</span>
      </div>
      <div class="meta-row">${eta}${altezza}</div>
      <div class="record">
        <div>
          <div class="value">${r.record_mma || "—"}</div>
        </div>
        <div class="last">${r.risultato_recente || ""} ${link}</div>
      </div>
    </div>`;
}

function renderGrid() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  let filtrati = roster;
  // Senza ricerca o filtro attivo, mostriamo solo le vere categorie di peso:
  // le sezioni speciali (release, sospesi...) hanno etichette troppo lunghe
  // per le card e interessano solo chi cerca quel lottatore per nome.
  if (!q && !categoriaAttiva) filtrati = filtrati.filter((r) => ORDINE_CATEGORIE.includes(r.categoria));
  if (categoriaAttiva === FILTRO_CAMPIONI) filtrati = filtrati.filter((r) => r.campione_attuale || r.ex_campione);
  else if (categoriaAttiva) filtrati = filtrati.filter((r) => r.categoria === categoriaAttiva);
  if (q) filtrati = filtrati.filter((r) => r.nome.toLowerCase().includes(q));

  document.getElementById("result-count").textContent = `(${filtrati.length})`;
  const grid = document.getElementById("fighter-grid");

  if (!filtrati.length) {
    grid.innerHTML = `<div class="empty-state">Nessun lottatore trovato.</div>`;
    return;
  }
  grid.innerHTML = filtrati.slice(0, 300).map(cardLottatore).join("");
}

async function init() {
  roster = await fetchJSON("data/roster.json");
  renderStatStrip();
  renderPills();
  renderGrid();
  document.getElementById("search").addEventListener("input", debounce(renderGrid, 120));
}

init();
