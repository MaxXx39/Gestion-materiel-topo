// Sauvegarde / restauration en un bouton, et exports Excel.
import { api, notifier, erreur, confirmer, zoneDepot } from "../outils.js";

export default async function pageSauvegarde(zone) {
  zone.innerHTML = `
    <div class="titre-page"><h1>Sauvegarde et exports</h1></div>
    <div class="deux-colonnes">
      <div class="carte">
        <h2>Sauvegarder</h2>
        <p>Télécharge un fichier <strong>.zip</strong> contenant <strong>toutes</strong> les données : articles, chantiers,
        affectations, photos et documents. Rangez-le sur une clé USB ou un disque réseau.</p>
        <p class="doux">Conseil : faites une sauvegarde au moins une fois par mois, par exemple après l'envoi du PDF à la compta.</p>
        <a class="bouton primaire-lien" href="/api/sauvegarde" id="sauver">⬇ Télécharger une sauvegarde</a>
      </div>
      <div class="carte">
        <h2>Restaurer</h2>
        <p>Remplace <strong>toutes</strong> les données actuelles par celles d'une sauvegarde (.zip).</p>
        <p class="doux">Par sécurité, une copie des données actuelles est d'abord enregistrée automatiquement dans le
        dossier <code>donnees\\sauvegardes_auto</code>.</p>
        <div class="zone-depot grande" id="restaurer">Glissez ici le fichier de sauvegarde (.zip)<br>ou cliquez pour le choisir</div>
      </div>
      <div class="carte">
        <h2>Exports Excel</h2>
        <p>Pour la compta, un tableau croisé ou un archivage.</p>
        <div class="actions">
          <a class="bouton" href="/api/export/inventaire.xlsx">⬇ Inventaire du parc (.xlsx)</a>
          <a class="bouton" href="/api/export/affectations.xlsx">⬇ Liste des affectations (.xlsx)</a>
        </div>
        <p class="doux">Le PDF et l'Excel mensuels se trouvent sur le planning (bouton « Exporter le mois »).</p>
      </div>
    </div>`;

  zone.querySelector("#sauver").addEventListener("click", () => notifier("Sauvegarde en cours de téléchargement…"));
  zoneDepot(zone.querySelector("#restaurer"), false, ".zip", async ([fichier]) => {
    const ok = await confirmer(
      `Remplacer toutes les données actuelles par la sauvegarde « ${fichier.name} » ? `
      + "Une copie de sécurité des données actuelles sera faite avant.",
      { titre: "Restaurer une sauvegarde", ok: "Restaurer", danger: true });
    if (!ok) return;
    const fd = new FormData();
    fd.append("fichier", fichier);
    try {
      const r = await api("POST", "/api/restauration", fd);
      notifier(`Sauvegarde restaurée. Copie de sécurité : ${r.securite}`);
      location.hash = "#/planning";
    } catch (e) { erreur(e); }
  });
}
