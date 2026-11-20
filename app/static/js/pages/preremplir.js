// Pré-remplissage : lit l'ancien planning Excel sur ce PC et crée catégories, articles et chantiers.
import { api, esc, notifier, erreur, confirmer, zoneDepot, dateAffichee } from "../outils.js";

export default async function pagePreremplir(zone) {
  zone.innerHTML = `
    <div class="titre-page">
      <a class="bouton" href="#/parc">◀ Parc</a>
      <h1>Importer depuis l'Excel</h1>
    </div>
    <div class="carte" id="etape-fichier">
      <p>Choisissez votre fichier Excel actuel (par exemple <strong>GESTION_GPS_V2.xlsx</strong>).
      L'application y lit les catégories, les articles (codes compta, couleurs), les numéros et noms des chantiers
      et les affectations (barres du planning). Les responsables ne sont pas repris. Le fichier est lu sur ce PC uniquement.</p>
      <div class="zone-depot grande">Glissez le fichier Excel ici<br>ou cliquez pour le choisir</div>
    </div>
    <div id="resultat"></div>`;

  zoneDepot(zone.querySelector(".zone-depot"), false, ".xlsx", async ([fichier]) => {
    const fd = new FormData();
    fd.append("fichier", fichier);
    try {
      const r = await api("POST", "/api/preremplissage/analyse", fd);
      afficherResultat(zone.querySelector("#resultat"), r, fichier.name);
    } catch (e) { erreur(e); }
  });
}

function afficherResultat(conteneur, r, nomFichier) {
  const nbVerifier = r.chantiers.filter((c) => c.a_verifier && !c.existe).length;
  conteneur.innerHTML = `
    <div class="carte" style="margin-top:16px">
      <h2>Articles trouvés dans « ${esc(nomFichier)} » (${r.articles.length})</h2>
      <p class="doux">Décochez ceux que vous ne voulez pas créer. Les articles déjà présents dans l'application sont ignorés.
      Vous pourrez tout modifier ensuite dans les fiches.</p>
      <table class="liste">
        <thead><tr><th><input type="checkbox" class="tout" data-t="articles" checked></th><th></th><th>Catégorie</th><th>Code compta</th><th>N° interne</th><th>État</th></tr></thead>
        <tbody>${r.articles.map((a, i) => `
          <tr class="${a.existe ? "inactif" : ""}">
            <td><input type="checkbox" data-a="${i}" ${a.existe ? "disabled" : "checked"}></td>
            <td><span class="echantillon" style="background:${esc(a.couleur)}"></span></td>
            <td>${esc(a.categorie)}</td>
            <td>${esc(a.code_compta)}</td>
            <td><strong>${esc(a.numero_interne)}</strong></td>
            <td>${a.existe ? '<span class="badge reforme">Existe déjà</span>' : '<span class="badge actif">Nouveau</span>'}</td>
          </tr>`).join("")}</tbody>
      </table>
    </div>

    <div class="carte" style="margin-top:16px">
      <h2>Chantiers trouvés (${r.chantiers.length})</h2>
      <p class="doux">Vérifiez le n° et le nom de chaque chantier (sans le responsable). La colonne de droite montre
      comment il est écrit dans l'Excel.
      ${nbVerifier ? `<strong class="attention">${nbVerifier} chantier${nbVerifier > 1 ? "s sont" : " est"} à vérifier</strong> : le découpage automatique n'est pas sûr.` : ""}</p>
      <div class="outils"><label class="case"><input type="checkbox" id="que-verifier"> N'afficher que les chantiers à vérifier</label></div>
      <table class="liste" id="table-chantiers">
        <thead><tr><th><input type="checkbox" class="tout" data-t="chantiers" checked></th><th style="width:120px">N°</th><th style="width:34%">Nom</th><th>Écrit dans l'Excel</th><th>État</th></tr></thead>
        <tbody>${r.chantiers.map((c, i) => `
          <tr class="${c.existe ? "inactif" : ""} ${c.a_verifier && !c.existe ? "a-verifier" : ""}" data-verifier="${c.a_verifier && !c.existe ? 1 : 0}">
            <td><input type="checkbox" data-c="${i}" ${c.existe ? "disabled" : "checked"}></td>
            <td><input data-numero="${i}" value="${esc(c.numero)}" ${c.existe ? "disabled" : ""}></td>
            <td><input data-nom="${i}" value="${esc(c.nom)}" ${c.existe ? "disabled" : ""}></td>
            <td class="doux">${c.textes.map(esc).join("<br>")}</td>
            <td>${c.existe ? '<span class="badge reforme">Existe déjà</span>'
              : c.a_verifier ? '<span class="badge reparation">À vérifier</span>' : '<span class="badge actif">Nouveau</span>'}</td>
          </tr>`).join("")}</tbody>
      </table>
    </div>

    ${r.affectations.length ? `
    <div class="carte" style="margin-top:16px">
      <h2>Affectations trouvées (${r.affectations.length})</h2>
      <p class="doux">Les barres coupées à chaque fin de mois dans l'Excel sont recollées. Le chantier affiché suit
      vos corrections du tableau ci-dessus.</p>
      <div class="outils">
        <label class="case"><input type="checkbox" id="importer-aff" checked> Importer les affectations</label>
        ${r.nb_existantes ? `<label class="case"><input type="checkbox" id="effacer"> Effacer d'abord les ${r.nb_existantes} affectation(s) déjà saisie(s)
          entre le ${dateAffichee(r.periode[0])} et le ${dateAffichee(r.periode[1])}</label>` : ""}
      </div>
      <table class="liste">
        <thead><tr><th>Article</th><th>Du</th><th>Au</th><th>Chantier</th><th>Écrit dans l'Excel</th></tr></thead>
        <tbody>${r.affectations.map((a, i) => `<tr>
          <td><strong>${esc(a.numero_interne)}</strong></td><td>${dateAffichee(a.date_debut)}</td><td>${dateAffichee(a.date_fin)}</td>
          <td data-aff-ch="${i}"></td><td class="doux">${esc(a.texte)}</td></tr>`).join("")}</tbody>
      </table>
    </div>` : (r.dates_trouvees ? "" : `<p class="attention">Les dates (ligne 2, à partir de D2) n'ont pas été trouvées : les affectations ne seront pas importées.</p>`)}

    <div class="actions barre-actions">
      <button class="primaire" id="valider">Importer la sélection</button>
      <span class="doux" id="resume"></span>
    </div>`;

  const $$ = (sel) => [...conteneur.querySelectorAll(sel)];
  const importerAff = () => !!conteneur.querySelector("#importer-aff")?.checked;
  const resume = () => {
    const na = $$("input[data-a]:checked").length, nc = $$("input[data-c]:checked").length;
    const nf = importerAff() ? r.affectations.length : 0;
    conteneur.querySelector("#resume").textContent =
      `${na} article(s), ${nc} chantier(s) et ${nf} affectation(s) seront importés.`;
    // Chantier affiché pour chaque affectation, d'après le tableau des chantiers.
    r.affectations.forEach((a, i) => {
      const j = r.chantiers.findIndex((c) => c.cle === a.cle);
      const td = conteneur.querySelector(`[data-aff-ch="${i}"]`);
      if (!td) return;
      if (j < 0) { td.textContent = "?"; return; }
      const num = conteneur.querySelector(`[data-numero="${j}"]`).value, nom = conteneur.querySelector(`[data-nom="${j}"]`).value;
      td.textContent = [num, nom].filter(Boolean).join(" – ");
    });
    return [na, nc, nf];
  };
  conteneur.addEventListener("input", (e) => { if (e.target.matches("[data-numero], [data-nom]")) resume(); });
  conteneur.addEventListener("change", (e) => {
    if (e.target.classList.contains("tout")) {
      const attr = e.target.dataset.t === "articles" ? "data-a" : "data-c";
      $$(`input[${attr}]:not(:disabled)`).forEach((x) => { x.checked = e.target.checked; });
    }
    if (e.target.id === "que-verifier") {
      $$("#table-chantiers tbody tr").forEach((tr) => { tr.hidden = e.target.checked && tr.dataset.verifier !== "1"; });
    }
    resume();
  });
  resume();

  conteneur.querySelector("#valider").onclick = async () => {
    const articles = $$("input[data-a]:checked").map((x) => r.articles[x.dataset.a]);
    // Les chantiers déjà présents sont aussi envoyés (sans être recréés) pour relier les affectations.
    const chantiers = r.chantiers.map((c, i) => ({ c, i })).filter(({ c, i }) => c.existe || conteneur.querySelector(`[data-c="${i}"]`).checked)
      .map(({ c, i }) => ({
        cle: c.cle,
        numero: conteneur.querySelector(`[data-numero="${i}"]`).value,
        nom: conteneur.querySelector(`[data-nom="${i}"]`).value,
      }));
    if (chantiers.some((c) => !c.nom.trim())) { erreur(new Error("Chaque chantier coché doit avoir un nom.")); return; }
    const affectations = importerAff() ? r.affectations : [];
    const effacer = !!conteneur.querySelector("#effacer")?.checked;
    const [na, nc, nf] = resume();
    const msg = `Importer ${na} article(s), ${nc} chantier(s) et ${nf} affectation(s) ?`
      + (effacer ? ` Les affectations déjà saisies sur la période seront effacées.` : "");
    if (!(await confirmer(msg, { titre: "Import", ok: "Importer" }))) return;
    try {
      const c = await api("POST", "/api/preremplissage/valider", { articles, chantiers, affectations, effacer });
      notifier(`Importés : ${c.categories} catégorie(s), ${c.articles} article(s), ${c.chantiers} chantier(s), ${c.affectations} affectation(s).`);
      if (c.refusees.length) {
        afficherRefusees(c.refusees);
      } else {
        location.hash = nf ? "#/planning" : "#/parc";
      }
    } catch (e) { erreur(e); }
  };
}

function afficherRefusees(refusees) {
  const dlg = document.createElement("dialog");
  dlg.innerHTML = `<div class="contenu">
    <h2>${refusees.length} affectation(s) non importée(s)</h2>
    <p class="doux">Elles sont listées ici pour que vous les ajoutiez ou corrigiez vous-même sur le planning.</p>
    <table class="liste"><thead><tr><th>Article</th><th>Du</th><th>Au</th><th>Texte</th><th>Motif</th></tr></thead>
    <tbody>${refusees.map((a) => `<tr><td>${esc(a.numero_interne)}</td><td>${dateAffichee(a.date_debut)}</td>
      <td>${dateAffichee(a.date_fin)}</td><td>${esc(a.texte)}</td><td>${esc(a.motif)}</td></tr>`).join("")}</tbody></table>
    <div class="actions"><button class="primaire" data-ok>Aller au planning</button></div></div>`;
  dlg.style.width = "min(900px, 96vw)";
  document.body.appendChild(dlg);
  dlg.querySelector("[data-ok]").onclick = () => dlg.close();
  dlg.addEventListener("close", () => { dlg.remove(); location.hash = "#/planning"; });
  dlg.showModal();
}
