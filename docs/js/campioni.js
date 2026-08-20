import { fetchJSON, renderChrome, icon, slugDaLink } from "./common.js";
import { ORGANIZZAZIONI } from "./europa-data.js";

renderChrome("campioni");

const ORDINE_CATEGORIE = [
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

function nomeBreveCategoria(cat) {
  return (cat || "").replace(/\s*\([^)]*\)/, "");
}

function cardCampione(r) {
  const href = r.slug ? `lottatore.html?slug=${r.slug}` : "#";
  const foto = r.foto
    ? `<img src="${r.foto}" alt="" onerror="this.parentElement.classList.add('senza-foto')" class="champ-foto">`
    : "";
  return `
    <a href="${href}" class="champ-card${r.foto ? "" : " senza-foto"}">
      ${foto}
      <div class="champ-overlay">
        <span class="champ-div">${nomeBreveCategoria(r.categoria)}</span>
        <div class="champ-nome-grande">${r.nome}</div>
        <div class="champ-record-grande">${r.record_mma || ""}</div>
      </div>
    </a>`;
}

function cardLeggenda(r) {
  const href = r.slug ? `lottatore.html?slug=${r.slug}` : null;
  const foto = r.foto
    ? `<img src="${r.foto}" alt="" onerror="this.style.display='none'" class="card-foto">`
    : `<div class="card-foto card-foto-placeholder">${(r.nome || "?").charAt(0)}</div>`;
  return `
    <div class="fighter-card">
      <div class="top-row">
        ${foto}
        <div style="flex:1; min-width:0;">
          <div class="name">${href ? `<a href="${href}">${r.nome}</a>` : r.nome}</div>
        </div>
      </div>
      <div class="record"><div><div class="value">${r.record_mma || "—"}</div></div></div>
    </div>`;
}

const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];

function rigaEventoBreve(ev) {
  const d = new Date(ev.data);
  const luogo = [ev.sede, ev.luogo].filter(Boolean).join(" — ");
  return `
    <div class="event-row">
      <div class="event-date"><span class="day">${isNaN(d) ? "?" : d.getDate()}</span><span class="month">${isNaN(d) ? "" : MESI[d.getMonth()] + " " + d.getFullYear()}</span></div>
      <div class="event-main">
        <div class="name">${ev.evento}</div>
        ${luogo ? `<div class="venue">${icon("pin")} ${luogo}</div>` : ""}
      </div>
      ${ev.link ? `<a class="event-link" href="evento.html?slug=${slugDaLink(ev.link)}">Dettagli →</a>` : "<span></span>"}
    </div>`;
}

function cardOrgBreve(org) {
  return `
    <div class="org-card">
      <div class="org-head">
        <div>
          <h2>${org.nome}</h2>
          <div class="org-sub">${org.paese} · dal ${org.fondata}</div>
        </div>
        ${org.id ? `<a href="organizzazione.html?org=${org.id}" class="event-link">Roster →</a>` : ""}
      </div>
      <div class="champ-list">
        ${org.campioni
          .slice(0, 3)
          .map((c) => `<div class="champ-row"><span class="champ-cat">${c.categoria}</span><span class="champ-nome">${c.nome}</span></div>`)
          .join("")}
      </div>
    </div>`;
}

async function init() {
  const roster = await fetchJSON("data/roster.json");

  const campioni = ORDINE_CATEGORIE.map((cat) => roster.find((r) => r.categoria === cat && r.campione_attuale)).filter(Boolean);
  document.getElementById("griglia-campioni").innerHTML = campioni.map(cardCampione).join("");

  const leggende = roster.filter((r) => r.ex_campione);
  document.getElementById("griglia-leggende").innerHTML = leggende.map(cardLeggenda).join("");

  const eventi = await fetchJSON("data/eventi.json");
  const prossimi = eventi
    .filter((e) => e.stato === "programmato")
    .sort((a, b) => new Date(a.data) - new Date(b.data))
    .slice(0, 4);
  document.getElementById("anteprima-eventi").innerHTML = prossimi.map(rigaEventoBreve).join("");

  document.getElementById("anteprima-europa").innerHTML = ORGANIZZAZIONI.map(cardOrgBreve).join("");
}

init();
