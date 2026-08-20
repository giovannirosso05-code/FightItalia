import { renderChrome } from "./common.js";
import { ORGANIZZAZIONI } from "./europa-data.js";

renderChrome("europa");

function cardOrganizzazione(org) {
  return `
    <div class="org-card">
      <div class="org-head">
        <div>
          <h2>${org.nome}</h2>
          <div class="org-sub">${org.nomeCompleto} · ${org.paese} · dal ${org.fondata}</div>
        </div>
        ${org.id ? `<a href="organizzazione.html?org=${org.id}" class="event-link">Roster ed eventi →</a>` : ""}
      </div>
      <p class="org-desc">${org.descrizione}</p>
      <div class="champ-list">
        ${org.campioni
          .map(
            (c) => `
          <div class="champ-row">
            <span class="champ-cat">${c.categoria}</span>
            <span class="champ-nome">${c.nome}</span>
          </div>`
          )
          .join("")}
      </div>
    </div>`;
}

document.getElementById("org-grid").innerHTML = ORGANIZZAZIONI.map(cardOrganizzazione).join("");
