import { fetchJSON, renderChrome, classeRisultato, letteraRisultato } from "./common.js";

renderChrome(null);

function rigaStorico(f) {
  const meta = [f.method, f.event].filter(Boolean).join(" · ");
  return `
    <div class="history-row">
      <div class="dot-result ${classeRisultato(f["res."])}">${letteraRisultato(f["res."])}</div>
      <div class="history-main">
        <div class="opp">${f.opponent || "—"}</div>
        ${meta ? `<div class="meta">${meta}</div>` : ""}
      </div>
      <div class="history-date">${f.date || ""}</div>
    </div>`;
}

function campoInfobox(k, v) {
  if (!v) return "";
  return `<div class="row"><span class="k">${k}</span><span class="v">${v}</span></div>`;
}

async function init() {
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug");
  const out = document.getElementById("profilo");

  if (!slug) {
    out.innerHTML = `<div class="empty-state">Lottatore non specificato. <a href="index.html">Torna al database</a>.</div>`;
    return;
  }

  let dett, roster;
  try {
    [dett, roster] = await Promise.all([
      fetchJSON(`data/lottatori/${slug}.json`),
      fetchJSON("data/roster.json"),
    ]);
  } catch (e) {
    out.innerHTML = `<div class="empty-state">Scheda non trovata. <a href="index.html">Torna al database</a>.</div>`;
    return;
  }

  const rigaRoster = roster.find((r) => r.slug === slug) || {};
  const inf = dett.infobox || {};
  const storico = dett.storico || [];
  const categoria = (inf["Division"] || rigaRoster.categoria || "").replace(/\s*\([^)]*\)/, "");

  out.innerHTML = `
    <section class="hero" style="padding:44px 0 24px; border-bottom:none;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
          <h1 style="font-size:clamp(28px,4vw,42px);">${dett.nome}</h1>
          ${inf["Other names"] || rigaRoster.soprannome ? `<p style="margin-top:6px; font-style:italic; color:var(--text-secondary);">"${inf["Other names"] || rigaRoster.soprannome}"</p>` : ""}
        </div>
        <div style="text-align:right;">
          <div style="font-family:var(--font-display); font-size:34px; color:var(--accent);">${rigaRoster.record_mma || "—"}</div>
          <span class="tag">${categoria || "—"}</span>
        </div>
      </div>
    </section>

    <div class="compare-grid" style="grid-template-columns:1fr; max-width:520px;">
      <div class="compare-col a">
        ${campoInfobox("Altezza", inf["Height"])}
        ${campoInfobox("Peso", inf["Weight"])}
        ${campoInfobox("Reach", inf["Reach"])}
        ${campoInfobox("Stile", inf["Fighting style"] || inf["Combat Style"])}
        ${campoInfobox("Team", inf["Team"])}
        ${campoInfobox("Nato", inf["Born"])}
        ${campoInfobox("Attivo dal", inf["Years active"])}
      </div>
    </div>

    <div class="section-title">Storico Incontri <span class="count">(${storico.length})</span></div>
    <div class="history-list" style="max-width:640px; max-height:600px;">
      ${storico.length ? storico.map(rigaStorico).join("") : `<div class="empty-state">Storico non disponibile.</div>`}
    </div>
  `;

  document.title = `${dett.nome} — MMA Hub`;
}

init();
