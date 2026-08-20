import {
  fetchJSON, renderChrome, cmDaStringa, numeroDaRecord,
  classeRisultato, letteraRisultato, debounce, slugDaLink, formDots,
} from "./common.js";

renderChrome("confronto");

const ORDINE_CATEGORIE = [
  "Heavyweights (265lb, 120 kg)", "Light heavyweights (205 lb, 93 kg)", "Middleweights (185 lb, 84 kg)",
  "Welterweights (170 lb, 77 kg)", "Lightweights (155 lb, 70 kg)", "Featherweights (145 lb, 65 kg)",
  "Bantamweights (135 lb, 61 kg)", "Flyweights (125 lb, 56 kg)",
];

let opzioni = [];
let scelti = { a: null, b: null };
let dettagli = { a: null, b: null };

function setupAutocomplete(chiave) {
  const wrap = document.getElementById(`picker-${chiave}`);
  const input = wrap.querySelector("input");
  const lista = wrap.querySelector(".autocomplete-list");
  let evidenziato = -1;

  function render(query) {
    const q = query.trim().toLowerCase();
    const risultati = (q ? opzioni.filter((o) => o.nome.toLowerCase().includes(q)) : opzioni).slice(0, 8);
    evidenziato = -1;
    if (!risultati.length) {
      lista.classList.remove("open");
      lista.innerHTML = "";
      return;
    }
    lista.innerHTML = risultati
      .map((o, i) => `<div data-idx="${i}"><div>${o.nome}</div><div class="sub">${(o.categoria || "").replace(/\s*\([^)]*\)/, "")}</div></div>`)
      .join("");
    lista.classList.add("open");
    [...lista.children].forEach((el, i) => {
      el.addEventListener("mousedown", () => selezionaOpzione(risultati[i]));
    });
  }

  function selezionaOpzione(o) {
    scelti[chiave] = o;
    input.value = o.nome;
    lista.classList.remove("open");
    aggiornaConfronto();
  }

  input.addEventListener("input", debounce(() => render(input.value), 100));
  input.addEventListener("focus", () => render(input.value));
  input.addEventListener("blur", () => setTimeout(() => lista.classList.remove("open"), 150));
  input.addEventListener("keydown", (e) => {
    const righe = [...lista.children];
    if (e.key === "ArrowDown") { evidenziato = Math.min(evidenziato + 1, righe.length - 1); }
    else if (e.key === "ArrowUp") { evidenziato = Math.max(evidenziato - 1, 0); }
    else if (e.key === "Enter" && evidenziato >= 0) { righe[evidenziato].dispatchEvent(new Event("mousedown")); return; }
    else return;
    righe.forEach((el, i) => el.classList.toggle("highlighted", i === evidenziato));
  });
}

function rigaInfo(k, v) {
  return `<div class="row"><span class="k">${k}</span><span class="v">${v || "—"}</span></div>`;
}

function colonna(dett, chiave, record, badge) {
  const inf = dett.infobox || {};
  const foto = inf["_immagine"];
  return `
    <div class="compare-col ${chiave}">
      ${foto ? `<img src="${foto}" alt="${dett.nome}" onerror="this.style.display='none'" style="width:72px; height:72px; object-fit:cover; border-radius:var(--radius); border:1px solid var(--border-soft); margin-bottom:10px;">` : ""}
      <h2><a href="lottatore.html?slug=${slugDaLink(dett.link)}">${dett.nome}</a></h2>
      <div class="compare-record">${record || "—"}</div>
      ${badge ? `<span class="tag numerato">${badge}</span>` : ""}
      ${rigaInfo("Categoria", inf["Division"])}
      ${rigaInfo("Altezza", inf["Height"])}
      ${rigaInfo("Reach", inf["Reach"])}
      ${rigaInfo("Team", inf["Team"])}
      ${rigaInfo("Attivo dal", inf["Years active"])}
      ${formDots(dett.storico)}
    </div>`;
}

function barraCoppia(label, valA, valB) {
  const a = valA || 0, b = valB || 0;
  const tot = a + b || 1;
  return `
    <div class="metric">
      <div class="label">${label}</div>
      <div class="pair">
        <div class="bar a" style="width:${(a / tot) * 100}%">${valA ?? "—"}</div>
        <div class="bar b" style="width:${(b / tot) * 100}%">${valB ?? "—"}</div>
      </div>
    </div>`;
}

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

function colonnaStorico(dett) {
  const storico = dett.storico || [];
  return `
    <div>
      <h3>${dett.nome} <span class="count">(${storico.length})</span></h3>
      <div class="history-list">
        ${storico.length ? storico.map(rigaStorico).join("") : `<div class="empty-state">Storico non disponibile.</div>`}
      </div>
    </div>`;
}

function testaATesta(dettA, dettB) {
  const storico = dettA.storico || [];
  const match = storico.find((f) => (f.opponent || "").toLowerCase().includes(dettB.nome.toLowerCase()));
  const box = document.createElement("div");
  if (match) {
    box.className = "head-to-head found";
    box.innerHTML = `Si sono già affrontati: <strong>${match["res."]}</strong> per ${dettA.nome} (${match.method || "—"}, ${match.event || "—"}, ${match.date || "—"})`;
  } else {
    box.className = "head-to-head";
    box.textContent = "Non risultano incontri diretti precedenti tra questi due lottatori.";
  }
  return box.outerHTML;
}

async function aggiornaConfronto() {
  const out = document.getElementById("risultato");
  if (!scelti.a || !scelti.b) return;
  if (scelti.a.link === scelti.b.link) {
    out.innerHTML = `<div class="empty-state">Scegli due lottatori diversi per confrontarli.</div>`;
    return;
  }
  out.innerHTML = `<div class="empty-state">Carico i dati...</div>`;

  const [dA, dB] = await Promise.all([
    fetchJSON(`data/lottatori/${scelti.a.slug}.json`),
    fetchJSON(`data/lottatori/${scelti.b.slug}.json`),
  ]);
  dettagli = { a: dA, b: dB };

  const altezzaA = cmDaStringa(dA.infobox?.Height), altezzaB = cmDaStringa(dB.infobox?.Height);
  const reachA = cmDaStringa(dA.infobox?.Reach), reachB = cmDaStringa(dB.infobox?.Reach);
  const [vintA, persA] = numeroDaRecord(scelti.a.record_mma);
  const [vintB, persB] = numeroDaRecord(scelti.b.record_mma);

  const badgeDi = (r) => (r.campione_attuale ? "Campione in carica" : r.ex_campione ? "Ex campione" : "");

  out.innerHTML = `
    <div class="compare-grid">
      ${colonna(dA, "a", scelti.a.record_mma, badgeDi(scelti.a))}
      <div class="vs-divider">VS</div>
      ${colonna(dB, "b", scelti.b.record_mma, badgeDi(scelti.b))}
    </div>
    <div class="bar-compare">
      ${barraCoppia("Reach (cm)", reachA, reachB)}
      ${barraCoppia("Altezza (cm)", altezzaA, altezzaB)}
      ${barraCoppia("Vittorie", vintA, vintB)}
      ${barraCoppia("Sconfitte", persA, persB)}
    </div>
    ${testaATesta(dA, dB)}

    <div class="section-title">Storico Incontri</div>
    <div class="history-columns">
      ${colonnaStorico(dA)}
      ${colonnaStorico(dB)}
    </div>
  `;
}

async function init() {
  const roster = await fetchJSON("data/roster.json");
  opzioni = roster.filter((r) => r.link && r.slug);

  setupAutocomplete("a");
  setupAutocomplete("b");

  const conPagina = opzioni.filter((o) => ORDINE_CATEGORIE.includes(o.categoria));
  if (conPagina.length >= 2) {
    scelti.a = conPagina[0];
    scelti.b = conPagina[1];
    document.querySelector("#picker-a input").value = conPagina[0].nome;
    document.querySelector("#picker-b input").value = conPagina[1].nome;
    aggiornaConfronto();
  }
}

init();
