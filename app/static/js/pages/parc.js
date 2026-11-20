// Liste du parc : recherche, filtres, tri, « Où est-il aujourd'hui ? ».
import { api, esc, normaliser, badgeStatut, dateAffichee, libelleChantier, comparer, STATUTS } from "../outils.js";

// Filtres conservés quand on revient sur la page.
const memo = { q: "", categorie: "", statut: "actif", dispo: "", tri: null, sens: 1 };

const COLONNES = [
  { cle: "couleur", titre: "", tri: null },
  { cle: "categorie", titre: "Catégorie", tri: (a) => a.categorie_ordre * 100000 + a.ordre },
  { cle: "numero", titre: "N° interne", tri: "numero_interne" },
  { cle: "designation", titre: "Désignation", tri: "designation" },
  { cle: "code", titre: "Code compta", tri: "code_compta" },
  { cle: "marque", titre: "Marque / modèle", tri: (a) => `${a.marque} ${a.modele}`.trim() },
  { cle: "serie", titre: "N° de série", tri: "numero_serie" },
  { cle: "statut", titre: "Statut", tri: (a) => STATUTS[a.statut] },
  { cle: "ou", titre: "Où est-il aujourd'hui ?", tri: (a) => ou(a) },
  { cle: "depuis", titre: "Depuis", tri: (a) => a.aujourdhui?.date_debut || "" },
];

function ou(a) {
  if (a.aujourdhui) {
    const x = a.aujourdhui;
    return libelleChantier(x.chantier_numero, x.chantier_nom, x.responsable);
  }
  return a.statut === "actif" ? "Disponible" : "—";
}

export default async function pageParc(zone) {
  const [articles, categories] = await Promise.all([api("GET", "/api/articles"), api("GET", "/api/categories")]);

  zone.innerHTML = `
    <div class="titre-page">
      <h1>Parc matériel</h1>
      <span class="espace"></span>
      <a class="bouton" href="#/preremplir">Importer depuis l'Excel</a>
      <a class="bouton" href="/api/export/inventaire.xlsx">⬇ Excel</a>
      <button class="primaire" id="ajouter">＋ Ajouter un matériel</button>
    </div>
    <div class="outils">
      <input type="search" id="q" placeholder="Rechercher (n°, désignation, série, chantier…)" value="${esc(memo.q)}">
      <select id="categorie">
        <option value="">Toutes les catégories</option>
        ${categories.map((c) => `<option value="${c.id}">${esc(c.nom)}</option>`).join("")}
      </select>
      <select id="statut">
        <option value="actif">Actifs</option>
        <option value="">Tous les statuts</option>
        ${Object.entries(STATUTS).filter(([k]) => k !== "actif").map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}
      </select>
      <select id="dispo">
        <option value="">Affectés et disponibles</option>
        <option value="dispo">Disponibles aujourd'hui</option>
        <option value="affecte">Affectés aujourd'hui</option>
      </select>
      <span class="compteur" id="compteur"></span>
    </div>
    <table class="liste">
      <thead><tr>${COLONNES.map((c) => `<th class="${c.tri ? "triable" : ""}" data-col="${c.cle}">${esc(c.titre)} <span class="fleche"></span></th>`).join("")}</tr></thead>
      <tbody id="lignes"></tbody>
    </table>`;

  const $ = (id) => zone.querySelector(`#${id}`);
  $("categorie").value = memo.categorie;
  $("statut").value = memo.statut;
  $("dispo").value = memo.dispo;
  $("ajouter").onclick = () => {
    location.hash = memo.categorie ? `#/article/nouveau?cat=${memo.categorie}` : "#/article/nouveau";
  };

  function dessiner() {
    const q = normaliser(memo.q);
    let liste = articles.filter((a) => {
      if (memo.categorie && String(a.categorie_id) !== memo.categorie) return false;
      if (memo.statut && a.statut !== memo.statut) return false;
      if (memo.dispo === "dispo" && (a.aujourdhui || a.statut !== "actif")) return false;
      if (memo.dispo === "affecte" && !a.aujourdhui) return false;
      if (q) {
        const texte = normaliser([a.numero_interne, a.designation, a.categorie_nom, a.code_compta, a.marque,
          a.modele, a.numero_serie, a.fournisseur, ou(a)].join(" "));
        if (!q.split(/\s+/).every((mot) => texte.includes(mot))) return false;
      }
      return true;
    });
    const col = COLONNES.find((c) => c.cle === memo.tri);
    if (col) liste = [...liste].sort(comparer(col.tri, memo.sens));

    zone.querySelectorAll("th").forEach((th) => {
      th.querySelector(".fleche").textContent = th.dataset.col === memo.tri ? (memo.sens > 0 ? "▲" : "▼") : "";
    });
    $("compteur").textContent = `${liste.length} article${liste.length > 1 ? "s" : ""}`;

    if (!liste.length) {
      const msg = articles.length
        ? "Aucun article ne correspond à ces filtres."
        : "Le parc est vide. Cliquez sur « Pré-remplir depuis l'Excel » pour reprendre votre fichier actuel, ou sur « Ajouter un matériel ».";
      $("lignes").innerHTML = `<tr><td class="vide" colspan="${COLONNES.length}">${esc(msg)}</td></tr>`;
      return;
    }
    $("lignes").innerHTML = liste.map((a) => {
      const lieu = ou(a);
      return `<tr class="cliquable ${a.statut !== "actif" ? "inactif" : ""}" data-id="${a.id}">
        <td><span class="echantillon" style="background:${esc(a.couleur)}"></span></td>
        <td>${esc(a.categorie_nom)}</td>
        <td><strong>${esc(a.numero_interne)}</strong></td>
        <td>${esc(a.designation)}${a.parent_numero ? ` <span class="doux">(accessoire de ${esc(a.parent_numero)})</span>` : ""}</td>
        <td>${esc(a.code_compta)}</td>
        <td>${esc(`${a.marque} ${a.modele}`.trim())}</td>
        <td>${esc(a.numero_serie)}</td>
        <td>${badgeStatut(a.statut)}</td>
        <td>${lieu === "Disponible" ? '<span class="dispo">Disponible</span>' : esc(lieu)}</td>
        <td>${a.aujourdhui ? dateAffichee(a.aujourdhui.date_debut) : ""}</td>
      </tr>`;
    }).join("");
  }

  $("q").oninput = (e) => { memo.q = e.target.value; dessiner(); };
  $("categorie").onchange = (e) => { memo.categorie = e.target.value; dessiner(); };
  $("statut").onchange = (e) => { memo.statut = e.target.value; dessiner(); };
  $("dispo").onchange = (e) => { memo.dispo = e.target.value; dessiner(); };
  zone.querySelector("thead").onclick = (e) => {
    const th = e.target.closest("th.triable");
    if (!th) return;
    if (memo.tri === th.dataset.col) memo.sens = -memo.sens;
    else { memo.tri = th.dataset.col; memo.sens = 1; }
    dessiner();
  };
  $("lignes").onclick = (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (tr) location.hash = `#/article/${tr.dataset.id}`;
  };
  dessiner();
  $("q").focus();
}
