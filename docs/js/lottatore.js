import { fetchJSON, renderChrome, classeRisultato, letteraRisultato, formDots, cmDaStringa, numeroDaRecord, debounce, metodoVittorie, badgeStreak } from "./common.js";

renderChrome(null);

let roster = [];
let dettCorrente = null;
let rigaCorrente = null;

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

function pannelloComeVince(storico) {
  const m = metodoVittorie(storico);
  if (!m.totale) return "";
  const pct = (n) => Math.round((n / m.totale) * 100);
  return `
    <div class="section-title" style="margin-top:40px;">Come vince</div>
    <div class="compare-col a" style="max-width:520px;">
      ${campoInfobox("KO/TKO", `${m.ko} (${pct(m.ko)}%)`)}
      ${campoInfobox("Sottomissione", `${m.sub} (${pct(m.sub)}%)`)}
      ${campoInfobox("Decisione", `${m.dec} (${pct(m.dec)}%)`)}
    </div>`;
}

function dataItaliana(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d) ? null : d.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

// Wikipedia (la nostra fonte) non riporta striking accuracy o takedown %/
// difesa — sono statistiche specifiche di UFCStats.com, che abbiamo escluso
// (protezione anti-bot, vedi README). Il campo resta qui pronto: se in
// futuro si aggiunge una fonte con questi dati, basta popolare
// inf["Striking accuracy"] / inf["Takedown accuracy"] / inf["Takedown defense"]
// e comparirà automaticamente invece di essere omesso.
function righeAvanzate(inf) {
  return [
    campoInfobox("Striking accuracy", inf["Striking accuracy"]),
    campoInfobox("Takedown accuracy", inf["Takedown accuracy"]),
    campoInfobox("Takedown defense", inf["Takedown defense"]),
  ].join("");
}

async function caricaLottatore(slug) {
  const [dett, rosterFresco] = await Promise.all([
    fetchJSON(`data/lottatori/${slug}.json`),
    roster.length ? Promise.resolve(roster) : fetchJSON("data/roster.json"),
  ]);
  roster = rosterFresco;
  const riga = roster.find((r) => r.slug === slug) || {};
  return { dett, riga };
}

function rigaTestaATesta(etichetta, vA, vB) {
  return `
    <div class="tt-row">
      <span class="v">${vA ?? "—"}</span>
      <span class="k">${etichetta}</span>
      <span class="v">${vB ?? "—"}</span>
    </div>`;
}

async function renderTestaATesta(slugA, dettA, rigaA) {
  const box = document.getElementById("testa-a-testa-risultato");
  const infA = dettA.infobox || {};
  const [vintA, persA] = numeroDaRecord(rigaA.record_mma);

  const opzioni = roster.filter((r) => r.link && r.slug && r.slug !== slugA);
  const wrap = document.getElementById("tt-picker");
  wrap.innerHTML = `
    <div class="autocomplete" id="tt-autocomplete">
      <input type="text" placeholder="Cerca un secondo lottatore da confrontare...">
      <div class="autocomplete-list"></div>
    </div>`;

  const input = wrap.querySelector("input");
  const lista = wrap.querySelector(".autocomplete-list");

  input.addEventListener("input", debounce(() => {
    const q = input.value.trim().toLowerCase();
    const risultati = (q ? opzioni.filter((o) => o.nome.toLowerCase().includes(q)) : opzioni).slice(0, 8);
    if (!risultati.length) { lista.classList.remove("open"); return; }
    lista.innerHTML = risultati.map((o) => `<div data-slug="${o.slug}"><div>${o.nome}</div><div class="sub">${(o.categoria || "").replace(/\s*\([^)]*\)/, "")}</div></div>`).join("");
    lista.classList.add("open");
    lista.querySelectorAll("div[data-slug]").forEach((el) => {
      el.addEventListener("mousedown", async () => {
        const rigaB = roster.find((r) => r.slug === el.dataset.slug);
        input.value = rigaB.nome;
        lista.classList.remove("open");
        const dettB = await fetchJSON(`data/lottatori/${rigaB.slug}.json`);
        mostraConfronto(rigaB, dettB);
      });
    });
  }, 100));
  input.addEventListener("blur", () => setTimeout(() => lista.classList.remove("open"), 150));

  function mostraConfronto(rigaB, dettB) {
    const infB = dettB.infobox || {};
    const [vintB, persB] = numeroDaRecord(rigaB.record_mma);
    box.innerHTML = `
      <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-family:var(--font-display); text-transform:uppercase; font-size:14px;">
        <a href="lottatore.html?slug=${slugA}">${dettA.nome}</a>
        <span style="color:var(--accent);">VS</span>
        <a href="lottatore.html?slug=${rigaB.slug}">${dettB.nome}</a>
      </div>
      ${rigaTestaATesta("Record", rigaA.record_mma, rigaB.record_mma)}
      ${rigaTestaATesta("Età", rigaA.eta ? rigaA.eta + " anni" : null, rigaB.eta ? rigaB.eta + " anni" : null)}
      ${rigaTestaATesta("Reach", infA["Reach"], infB["Reach"])}
      ${rigaTestaATesta("Stile", infA["Style"], infB["Style"])}
      ${rigaTestaATesta("Striking accuracy", infA["Striking accuracy"], infB["Striking accuracy"])}
      ${rigaTestaATesta("Takedown %", infA["Takedown accuracy"], infB["Takedown accuracy"])}
      <div class="tt-row">
        <span class="v">${formDots(dettA.storico)}</span>
        <span class="k">Ultimi 5</span>
        <span class="v">${formDots(dettB.storico)}</span>
      </div>
    `;
  }
}

async function init() {
  const params = new URLSearchParams(location.search);
  const slug = params.get("slug");
  const out = document.getElementById("profilo");

  if (!slug) {
    out.innerHTML = `<div class="empty-state">Lottatore non specificato. <a href="index.html">Torna al database</a>.</div>`;
    return;
  }

  let dett, rigaRoster;
  try {
    const risultato = await caricaLottatore(slug);
    dett = risultato.dett;
    rigaRoster = risultato.riga;
  } catch (e) {
    out.innerHTML = `<div class="empty-state">Scheda non trovata. <a href="index.html">Torna al database</a>.</div>`;
    return;
  }

  dettCorrente = dett;
  rigaCorrente = rigaRoster;

  const inf = dett.infobox || {};
  const storico = dett.storico || [];
  const categoria = (inf["Division"] || rigaRoster.categoria || "").replace(/\s*\([^)]*\)/, "");
  const foto = inf["_immagine"];
  const badge = rigaRoster.campione_attuale
    ? `<span class="tag numerato">Campione in carica</span>`
    : rigaRoster.ex_campione
    ? `<span class="tag numerato">Ex campione</span>`
    : "";
  const dataAgg = dataItaliana(dett.ultimo_aggiornamento);
  const rigaAvanzate = righeAvanzate(inf);

  out.innerHTML = `
    <section class="hero" style="padding:44px 0 24px; border-bottom:none;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
        <div>
          <h1 style="font-size:clamp(28px,4vw,42px);">${dett.nome}</h1>
          ${inf["Other names"] || rigaRoster.soprannome ? `<p style="margin-top:6px; font-style:italic; color:var(--text-secondary);">"${inf["Other names"] || rigaRoster.soprannome}"</p>` : ""}
          ${badge ? `<div style="margin-top:8px;">${badge}</div>` : ""}
          ${dataAgg ? `<p style="margin-top:10px; font-size:12px; color:var(--text-muted);">Dati aggiornati al: ${dataAgg}</p>` : ""}
        </div>
        <div style="text-align:right;">
          <div style="font-family:var(--font-display); font-size:34px; color:var(--accent);">${rigaRoster.record_mma || "—"}</div>
          <span class="tag">${categoria || "—"}</span>
        </div>
      </div>
      ${foto ? `<img src="${foto}" alt="${dett.nome}" onerror="this.style.display='none'" class="foto-lottatore-grande">` : ""}
    </section>

    <div class="compare-grid" style="grid-template-columns:1fr; max-width:520px;">
      <div class="compare-col a">
        ${campoInfobox("Altezza", inf["Height"])}
        ${campoInfobox("Peso", inf["Weight"])}
        ${campoInfobox("Reach", inf["Reach"])}
        ${campoInfobox("Stile", inf["Style"] || inf["Fighting style"] || inf["Combat Style"])}
        ${campoInfobox("Team", inf["Team"])}
        ${campoInfobox("Nato", inf["Born"])}
        ${campoInfobox("Attivo dal", inf["Years active"])}
        ${rigaAvanzate}
      </div>
      ${storico.length ? `<div style="margin-top:6px;"><span class="row .k" style="color:var(--text-muted); font-size:12px;">Ultimi 5 incontri</span><div style="margin-top:6px;">${formDots(storico)}${badgeStreak(storico)}</div></div>` : ""}
    </div>

    ${pannelloComeVince(storico)}

    <div class="section-title" style="margin-top:40px;">Testa a testa</div>
    <div id="tt-picker" style="max-width:520px;"></div>
    <div id="testa-a-testa-risultato" style="max-width:520px; margin-top:16px;"></div>

    <div class="section-title">Storico Incontri <span class="count">(${storico.length})</span></div>
    <div class="history-list" style="max-width:640px; max-height:600px;">
      ${storico.length ? storico.map(rigaStorico).join("") : `<div class="empty-state">Storico non disponibile.</div>`}
    </div>
  `;

  document.title = `${dett.nome} — FightItalia`;
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) {
    metaDesc.setAttribute(
      "content",
      `${dett.nome} — ${categoria || "MMA"}, record ${rigaRoster.record_mma || "n/d"}. Statistiche, storico incontri e confronto su FightItalia.`
    );
  }

  renderTestaATesta(slug, dett, rigaRoster);
}

init();
