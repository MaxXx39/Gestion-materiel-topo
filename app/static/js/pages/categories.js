// Catégories et ordre d'affichage des articles (le même ordre sert au planning et au PDF).
import { api, esc, notifier, erreur, confirmer, demanderTexte, badgeStatut } from "../outils.js";

export default async function pageCategories(zone) {
  const [categories, articles] = await Promise.all([api("GET", "/api/categories"), api("GET", "/api/articles")]);

  zone.innerHTML = `
    <div class="titre-page">
      <h1>Catégories et ordre</h1>
      <span class="espace"></span>
      <button class="primaire" id="nouvelle">＋ Nouvelle catégorie</button>
    </div>
    <p class="doux">L'ordre ci-dessous est celui du planning et du PDF mensuel. Utilisez ▲ ▼ pour le modifier.</p>
    <div id="blocs"></div>`;

  const blocs = zone.querySelector("#blocs");
  blocs.innerHTML = categories.length ? categories.map((c, i) => {
    const as = articles.filter((a) => a.categorie_id === c.id);
    return `
      <div class="carte bloc-categorie" data-cat="${c.id}">
        <div class="tete">
          <button class="icone" data-action="cat-monter" ${i === 0 ? "disabled" : ""} title="Monter">▲</button>
          <button class="icone" data-action="cat-descendre" ${i === categories.length - 1 ? "disabled" : ""} title="Descendre">▼</button>
          <strong>${esc(c.nom)}</strong>
          <span>${as.length} article${as.length > 1 ? "s" : ""}</span>
          <span class="espace"></span>
          <button data-action="ajouter">＋ Article</button>
          <button data-action="renommer">Renommer</button>
          <button data-action="supprimer" ${as.length ? "disabled title=\"Videz d'abord la catégorie\"" : ""}>Supprimer</button>
        </div>
        ${as.map((a, j) => `
          <div class="ligne-article" data-art="${a.id}">
            <button class="icone" data-action="art-monter" ${j === 0 ? "disabled" : ""} title="Monter">▲</button>
            <button class="icone" data-action="art-descendre" ${j === as.length - 1 ? "disabled" : ""} title="Descendre">▼</button>
            <span class="apercu-ligne"><span class="code">${esc(a.code_compta) || "&nbsp;"}</span><span style="background:${esc(a.couleur)};min-width:110px">${esc(a.numero_interne)}</span></span>
            <span class="nom"><a href="#/article/${a.id}">${esc(a.designation || a.numero_interne)}</a></span>
            ${badgeStatut(a.statut)}
          </div>`).join("") || `<div class="ligne-article doux">Aucun article dans cette catégorie.</div>`}
      </div>`;
  }).join("") : `<div class="carte message-attente">Aucune catégorie. Créez-en une, par exemple « Canne GPS ».</div>`;

  const recharger = () => pageCategories(zone);

  zone.querySelector("#nouvelle").onclick = async () => {
    const nom = await demanderTexte("Nouvelle catégorie", "", "Nom de la catégorie");
    if (!nom) return;
    try { await api("POST", "/api/categories", { nom }); notifier("Catégorie créée."); recharger(); } catch (e) { erreur(e); }
  };

  blocs.onclick = async (e) => {
    const b = e.target.closest("button[data-action]");
    if (!b) return;
    const catId = b.closest("[data-cat]").dataset.cat;
    const cat = categories.find((c) => String(c.id) === catId);
    const artId = b.closest("[data-art]")?.dataset.art;
    try {
      switch (b.dataset.action) {
        case "cat-monter": await api("POST", `/api/categories/${catId}/deplacer`, { sens: -1 }); break;
        case "cat-descendre": await api("POST", `/api/categories/${catId}/deplacer`, { sens: 1 }); break;
        case "art-monter": await api("POST", `/api/articles/${artId}/deplacer`, { sens: -1 }); break;
        case "art-descendre": await api("POST", `/api/articles/${artId}/deplacer`, { sens: 1 }); break;
        case "ajouter": location.hash = `#/article/nouveau?cat=${catId}`; return;
        case "renommer": {
          const nom = await demanderTexte("Renommer la catégorie", cat.nom, "Nom de la catégorie");
          if (!nom || nom === cat.nom) return;
          await api("PUT", `/api/categories/${catId}`, { nom });
          break;
        }
        case "supprimer":
          if (!(await confirmer(`Supprimer la catégorie « ${cat.nom} » ?`, { ok: "Supprimer", danger: true }))) return;
          await api("DELETE", `/api/categories/${catId}`);
          break;
        default: return;
      }
      recharger();
    } catch (err) { erreur(err); }
  };
}
