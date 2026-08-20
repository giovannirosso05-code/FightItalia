import { fetchJSON, renderChrome, debounce } from "./common.js";
import { ORGANIZZAZIONI } from "./europa-data.js";

renderChrome("europa");

function pulisciCategoria(cat) {
  if (!cat) return "—";
  return cat.replace(/\bIb\b/g, "lb").replace(/\s*\([^)]*\)/, "");
}

function cardLottatoreOrg(r) {
  const record = r["MMA record"] || r["MMA Record"] || "—";
  const recordOrg = r["KSW record"] || r["Oktagon record"] || null;
  return `
    <div class="fighter-card">
      <div class="top-row">
        <div>
          <div class="name">${r.nome}</div>
          ${r.Nickname ? `<div class="nickname">"${r.Nickname}"</div>` : ""}
        </div>
        <span class="tag">${pulisciCategoria(r.categoria)}</span>
      </div>
      <div class="meta-row">${r.Paese ? `<span>${r.Paese}</span>` : ""}</div>
      <div class="record">
        <div><div class="value">${record}</div></div>
        ${recordOrg ? `<div class="last">Nell'organizzazione: ${recordOrg}</div>` : ""}
      </div>
    </div>`;
}

function rigaEventoOrg(ev) {
  const luogo = [ev.sede, ev.luogo].filter(Boolean).join(" — ");
  const d = new Date(ev.data);
  const giorno = isNaN(d) ? "?" : d.getDate();
  const mese = isNaN(d) ? "" : d.toLocaleDateString("it-IT", { month: "short", year: "numeric" });
  return `
    <div class="event-row">
      <div class="event-date"><span class="day">${giorno}</span><span class="month">${mese}</span></div>
      <div class="event-main">
        <div class="name">${ev.evento}</div>
        ${luogo ? `<div class="venue">${luogo}</div>` : ""}
      </div>
      <span></span>
    </div>`;
}

async function init() {
  const params = new URLSearchParams(location.search);
  const orgId = params.get("org");
  const out = document.getElementById("pagina");

  const meta = ORGANIZZAZIONI.find((o) => o.id === orgId);
  if (!orgId) {
    out.innerHTML = `<div class="empty-state">Organizzazione non specificata. <a href="europa.html">Torna a Europa</a>.</div>`;
    return;
  }

  let roster = [], eventi = [];
  try { roster = await fetchJSON(`data/europa/${orgId}-roster.json`); } catch { roster = []; }
  try { eventi = await fetchJSON(`data/europa/${orgId}-eventi.json`); } catch { eventi = []; }

  const nomeOrg = meta ? meta.nome : orgId.toUpperCase();
  document.title = `${nomeOrg} — MMA Hub`;

  out.innerHTML = `
    <section class="hero" style="padding:44px 0 24px; border-bottom:none;">
      <h1 style="font-size:clamp(28px,4vw,42px);">${nomeOrg}</h1>
      ${meta ? `<p>${meta.descrizione}</p>` : ""}
      <div class="stat-strip">
        <div class="stat"><div class="value">${roster.length}</div><div class="label">Lottatori nel roster</div></div>
        <div class="stat"><div class="value">${eventi.length}</div><div class="label">Eventi (2025–2026)</div></div>
      </div>
    </section>

    <div class="org-tabs">
      <button class="org-tab active" data-tab="roster">Roster</button>
      <button class="org-tab" data-tab="eventi">Eventi</button>
    </div>

    <div id="tab-roster">
      <div class="filter-bar">
        <div class="search-input"><input id="ricerca-org" type="text" placeholder="Cerca un lottatore..."></div>
      </div>
      <div class="section-title">Roster <span class="count" id="count-org"></span></div>
      <div class="fighter-grid" id="grid-org"></div>
    </div>

    <div id="tab-eventi" style="display:none;">
      <div class="section-title" style="margin-top:24px;">Eventi</div>
      <div id="eventi-org">${eventi.length ? eventi.map(rigaEventoOrg).join("") : `<div class="empty-state">Nessun evento trovato per il periodo coperto.</div>`}</div>
    </div>

    <p style="margin:14px 0 60px; font-size:12px; color:var(--text-muted);">Roster ed eventi da Wikipedia. Scheda di dettaglio per singolo lottatore/evento non ancora disponibile per questa organizzazione (solo per UFC per ora).</p>
  `;

  function renderGrid() {
    const q = document.getElementById("ricerca-org").value.trim().toLowerCase();
    const filtrati = q ? roster.filter((r) => r.nome.toLowerCase().includes(q)) : roster;
    document.getElementById("count-org").textContent = `(${filtrati.length})`;
    const grid = document.getElementById("grid-org");
    grid.innerHTML = filtrati.length
      ? filtrati.slice(0, 300).map(cardLottatoreOrg).join("")
      : `<div class="empty-state">Nessun lottatore trovato.</div>`;
  }

  renderGrid();
  document.getElementById("ricerca-org").addEventListener("input", debounce(renderGrid, 120));

  document.querySelectorAll(".org-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".org-tab").forEach((b) => b.classList.toggle("active", b === btn));
      document.getElementById("tab-roster").style.display = btn.dataset.tab === "roster" ? "block" : "none";
      document.getElementById("tab-eventi").style.display = btn.dataset.tab === "eventi" ? "block" : "none";
    });
  });
}

init();
