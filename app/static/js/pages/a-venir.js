import { esc } from "../outils.js";

// Page provisoire pour les écrans des étapes suivantes.
export function pageAVenir(titre, message) {
  return async (zone) => {
    zone.innerHTML = `
      <div class="message-attente">
        <h1>${esc(titre)}</h1>
        <p>${esc(message)}</p>
        <p><a href="#/parc">Aller au parc matériel</a></p>
      </div>`;
  };
}
