// Utility condivise tra le pagine del sito.

export async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Errore caricando ${path}: ${res.status}`);
  return res.json();
}

const ICONS = {
  search: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  ruler: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17h18v4H3zM7 17v-3M11 17v-3M15 17v-3M19 17v-3M3 17L17 3l4 4L7 21z"/></svg>`,
  age: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg>`,
  pin: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s7-7.4 7-12a7 7 0 1 0-14 0c0 4.6 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>`,
  link: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></svg>`,
};

export function icon(name) {
  return ICONS[name] || "";
}

export function renderChrome(active) {
  const header = document.getElementById("site-header");
  if (header) {
    header.innerHTML = `
      <div class="container nav">
        <a href="index.html" class="brand">Fight<span class="dot">•</span>Italia</a>
        <ul class="nav-links">
          <li><a href="index.html" class="${active === "database" ? "active" : ""}">Lottatori</a></li>
          <li><a href="confronto.html" class="${active === "confronto" ? "active" : ""}">Confronto</a></li>
          <li><a href="eventi.html" class="${active === "eventi" ? "active" : ""}">Eventi</a></li>
          <li><a href="europa.html" class="${active === "europa" ? "active" : ""}">Europa</a></li>
          <li><a href="campioni.html" class="${active === "campioni" ? "active" : ""}">Campioni</a></li>
        </ul>
      </div>`;
  }
  const footer = document.getElementById("site-footer");
  if (footer) {
    footer.innerHTML = `
      <div class="container">
        <p style="margin:0 0 6px;">I dati riportati hanno scopo informativo e statistico; non costituiscono consiglio di scommessa. Gioca responsabilmente.</p>
        <p style="margin:0;">FightItalia — statistiche e confronti sugli sport da combattimento. Dati e immagini da Wikipedia (licenza CC BY-SA), aggiornati periodicamente. In Italia gli eventi UFC si seguono in streaming legale su DAZN.</p>
      </div>`;
  }
}

export function cmDaStringa(testo) {
  if (typeof testo !== "string") return null;
  const m = testo.match(/\(([\d.]+)\s*(cm|m)\)/);
  if (!m) return null;
  const valore = parseFloat(m[1]);
  return Math.round((m[2] === "m" ? valore * 100 : valore) * 10) / 10;
}

export function numeroDaRecord(record) {
  if (typeof record !== "string") return [null, null];
  const m = record.trim().match(/^(\d+)[–-](\d+)/);
  return m ? [parseInt(m[1], 10), parseInt(m[2], 10)] : [null, null];
}

export function classeRisultato(risultato) {
  const r = (risultato || "").trim().toLowerCase();
  if (r === "win") return "win";
  if (r === "loss") return "loss";
  if (r === "draw") return "draw";
  return "draw";
}

export function letteraRisultato(risultato) {
  const r = (risultato || "").trim().toLowerCase();
  if (r === "win") return "V";
  if (r === "loss") return "S";
  if (r === "draw") return "P";
  return "?";
}

export function debounce(fn, wait = 200) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

export function formDots(storico, n = 5) {
  if (!storico || !storico.length) return "";
  const ultimi = storico.slice(0, n);
  return `<div class="form-dots">${ultimi
    .map(
      (f) => `
      <div class="dot-result ${classeRisultato(f["res."])}" tabindex="0">
        ${letteraRisultato(f["res."])}
        <span class="dot-tooltip">${f["res."] || ""} vs ${f.opponent || "?"}<br>${f.method || ""}<br>${f.date || ""}</span>
      </div>`
    )
    .join("")}</div>`;
}

export function slugDaLink(link) {
  if (!link) return null;
  return link
    .replace(/\/$/, "")
    .split("/")
    .pop()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
