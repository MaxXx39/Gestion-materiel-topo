// Pré-remplissage : lit l'ancien planning Excel sur ce PC et crée catégories, articles et chantiers.
import { api, esc, notifier, erreur, confirmer, zoneDepot } from "../outils.js";

export default async function pagePreremplir(zone) {
  zone.innerHTML = `
    <div class="titre-page">
      <a class="bouton" href="#/parc">◀ Parc</a>
      <h1>Pré-remplir depuis l'Excel</h1>
    </div>
    <div class="carte" id="etape-fichier">
      <p>Choisissez votre fichier Excel actuel (par exemple <strong>GESTION_GPS_V2.xlsx</strong>).
      L'application y lit les catégories, les articles (codes compta, couleurs) et les numéros et noms des chantiers.
      Les responsables ne sont pas repris. Le fichier est lu sur ce PC uniquement.</p>
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

    <div class="actions barre-actions">
      <button class="primaire" id="valider">Créer les articles et chantiers cochés</button>
      <span class="doux" id="resume"></span>
    </div>`;

  const $$ = (sel) => [...conteneur.querySelectorAll(sel)];
  const resume = () => {
    const na = $$("input[data-a]:checked").length, nc = $$("input[data-c]:checked").length;
    conteneur.querySelector("#resume").textContent = `${na} article${na > 1 ? "s" : ""} et ${nc} chantier${nc > 1 ? "s" : ""} seront créés.`;
    return [na, nc];
  };
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
    const chantiers = $$("input[data-c]:checked").map((x) => ({
      numero: conteneur.querySelector(`[data-numero="${x.dataset.c}"]`).value,
      nom: conteneur.querySelector(`[data-nom="${x.dataset.c}"]`).value,
    }));
    const vides = chantiers.filter((c) => !c.nom.trim());
    if (vides.length) { erreur(new Error("Chaque chantier coché doit avoir un nom.")); return; }
    const [na, nc] = resume();
    if (!(await confirmer(`Créer ${na} article(s) et ${nc} chantier(s) ?`, { titre: "Pré-remplissage", ok: "Créer" }))) return;
    try {
      const c = await api("POST", "/api/preremplissage/valider", { articles, chantiers });
      notifier(`Créés : ${c.categories} catégorie(s), ${c.articles} article(s), ${c.chantiers} chantier(s).`
        + (c.ignores ? ` ${c.ignores} élément(s) déjà présent(s) ignoré(s).` : ""));
      location.hash = "#/parc";
    } catch (e) { erreur(e); }
  };
}
