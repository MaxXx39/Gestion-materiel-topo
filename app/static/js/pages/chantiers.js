// Liste des chantiers et fenêtre de création / modification.
import { api, esc, normaliser, notifier, erreur, confirmer, dateAffichee, comparer } from "../outils.js";

const memo = { q: "", archives: false };

export default async function pageChantiers(zone) {
  let chantiers = await api("GET", "/api/chantiers");

  zone.innerHTML = `
    <div class="titre-page">
      <h1>Chantiers</h1>
      <span class="espace"></span>
      <button class="primaire" id="nouveau">＋ Nouveau chantier</button>
    </div>
    <div class="outils">
      <input type="search" id="q" placeholder="Rechercher (n°, nom, responsable)" value="${esc(memo.q)}">
      <label class="case"><input type="checkbox" id="archives" ${memo.archives ? "checked" : ""}> Afficher les chantiers archivés</label>
      <span class="compteur" id="compteur"></span>
    </div>
    <table class="liste">
      <thead><tr><th>N° de chantier</th><th>Nom</th><th>Responsable</th><th>Facturable</th><th>Affectations</th><th>Dernière date</th><th>État</th></tr></thead>
      <tbody id="lignes"></tbody>
    </table>`;

  const $ = (id) => zone.querySelector(`#${id}`);

  function dessiner() {
    const q = normaliser(memo.q).replace(/\s/g, "");
    const liste = chantiers
      .filter((c) => memo.archives || !c.archive)
      .filter((c) => !q || normaliser(`${c.numero}${c.nom}${c.responsable}`).replace(/\s/g, "").includes(q))
      .sort(comparer((c) => `${c.archive}${c.numero ? "0" : "1"}${c.numero || c.nom}`));
    $("compteur").textContent = `${liste.length} chantier${liste.length > 1 ? "s" : ""}`;
    $("lignes").innerHTML = liste.length ? liste.map((c) => `
      <tr class="cliquable ${c.archive ? "inactif" : ""}" data-id="${c.id}">
        <td><strong>${esc(c.numero)}</strong></td>
        <td>${esc(c.nom)}</td>
        <td>${esc(c.responsable)}</td>
        <td>${c.facturable ? "Oui" : "<strong>Non</strong>"}</td>
        <td class="num">${c.nb_affectations}</td>
        <td>${dateAffichee(c.derniere_date)}</td>
        <td>${c.archive ? '<span class="badge reforme">Archivé</span>' : '<span class="badge actif">Actif</span>'}</td>
      </tr>`).join("")
      : `<tr><td class="vide" colspan="7">${chantiers.length ? "Aucun chantier ne correspond." : "Aucun chantier. Cliquez sur « Nouveau chantier »."}</td></tr>`;
  }

  async function recharger() { chantiers = await api("GET", "/api/chantiers"); dessiner(); }

  $("q").oninput = (e) => { memo.q = e.target.value; dessiner(); };
  $("archives").onchange = (e) => { memo.archives = e.target.checked; dessiner(); };
  $("nouveau").onclick = async () => { if (await fenetreChantier()) recharger(); };
  $("lignes").onclick = async (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (!tr) return;
    const c = chantiers.find((x) => String(x.id) === tr.dataset.id);
    if (await fenetreChantier(c)) recharger();
  };
  dessiner();
  $("q").focus();
}

// Fenêtre de saisie d'un chantier. Renvoie le chantier enregistré, ou null si annulé.
// Exportée pour être réutilisée par le planning (création à la volée).
export function fenetreChantier(chantier = null, valeursInitiales = {}) {
  const c = chantier || { numero: "", nom: "", responsable: "", facturable: 1, archive: 0, notes: "", ...valeursInitiales };
  return new Promise((resoudre) => {
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `
      <form method="dialog" autocomplete="off">
        <h2>${chantier ? "Modifier le chantier" : "Nouveau chantier"}</h2>
        <div class="champs">
          <label class="champ"><span>N° de chantier</span><input name="numero" placeholder="ex. 123 456"></label>
          <label class="champ"><span>Nom <b class="obligatoire">*</b></span><input name="nom" required placeholder="ex. Nom du chantier"></label>
          <label class="champ"><span>Responsable / conducteur</span><input name="responsable" placeholder="ex. M. Dupont"></label>
          <div class="champ"><span>&nbsp;</span>
            <label class="case"><input type="checkbox" name="facturable"> Facturable</label></div>
          <label class="champ large"><span>Notes</span><textarea name="notes" rows="2"></textarea></label>
          ${chantier ? `<label class="case large"><input type="checkbox" name="archive"> Archivé (n'apparaît plus dans les listes de choix)</label>` : ""}
        </div>
        <div class="actions">
          ${chantier ? `<button type="button" class="danger" data-sup style="margin-right:auto">Supprimer</button>` : ""}
          <button type="button" data-annuler>Annuler</button>
          <button class="primaire">Enregistrer</button>
        </div>
      </form>`;
    document.body.appendChild(dlg);
    const f = dlg.querySelector("form");
    f.elements.numero.value = c.numero || "";
    f.elements.nom.value = c.nom || "";
    f.elements.responsable.value = c.responsable || "";
    f.elements.notes.value = c.notes || "";
    f.elements.facturable.checked = !!c.facturable;
    if (f.elements.archive) f.elements.archive.checked = !!c.archive;

    let resultat = null;
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const donnees = {
        numero: f.elements.numero.value,
        nom: f.elements.nom.value,
        responsable: f.elements.responsable.value,
        notes: f.elements.notes.value,
        facturable: f.elements.facturable.checked,
        archive: f.elements.archive ? f.elements.archive.checked : false,
      };
      try {
        resultat = chantier
          ? await api("PUT", `/api/chantiers/${chantier.id}`, donnees)
          : await api("POST", "/api/chantiers", donnees);
        notifier("Chantier enregistré.");
        dlg.close();
      } catch (err) { erreur(err); }
    });
    dlg.querySelector("[data-annuler]").onclick = () => dlg.close();
    const sup = dlg.querySelector("[data-sup]");
    if (sup) sup.onclick = async () => {
      if (!(await confirmer(`Supprimer le chantier « ${c.numero} ${c.nom} » ?`, { ok: "Supprimer", danger: true }))) return;
      try {
        await api("DELETE", `/api/chantiers/${chantier.id}`);
        notifier("Chantier supprimé.");
        resultat = { supprime: true };
        dlg.close();
      } catch (err) { erreur(err); }
    };
    dlg.addEventListener("close", () => { dlg.remove(); resoudre(resultat); });
    dlg.showModal();
    (c.numero || chantier ? f.elements.nom : f.elements.numero).focus();
  });
}
