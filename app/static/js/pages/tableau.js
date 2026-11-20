// Tableau de bord : chiffres clés du parc et listes utiles pour la journée.
import { api, esc, chf, dateAffichee, aujourdhuiIso, libelleChantier, STATUTS } from "../outils.js";

export default async function pageTableau(zone) {
  const auj = aujourdhuiIso();
  const dans7 = new Date(auj + "T00:00:00Z");
  dans7.setUTCDate(dans7.getUTCDate() + 7);
  const fin7 = dans7.toISOString().slice(0, 10);
  const [articles, aff] = await Promise.all([
    api("GET", "/api/articles"),
    api("GET", `/api/affectations?debut=${auj}&fin=${fin7}`),
  ]);

  const parc = articles.filter((a) => a.statut !== "reforme");           // parc existant (hors réformés / vendus)
  const actifs = articles.filter((a) => a.statut === "actif");
  const affectes = actifs.filter((a) => a.aujourdhui);
  const dispo = actifs.filter((a) => !a.aujourdhui);
  const reparation = articles.filter((a) => a.statut === "reparation");
  const valeur = parc.filter((a) => a.statut !== "perdu").reduce((s, a) => s + (a.prix_chf || 0), 0);
  const sansPrix = parc.filter((a) => a.statut !== "perdu" && !a.prix_chf).length;
  const parId = Object.fromEntries(articles.map((a) => [a.id, a]));
  const fins = aff.affectations.filter((x) => x.date_fin >= auj && x.date_fin <= fin7).sort((x, y) => x.date_fin.localeCompare(y.date_fin));

  const ligneArticle = (a, extra = "") => `
    <a class="ligne-tableau" href="#/article/${a.id}">
      <span class="echantillon" style="background:${esc(a.couleur)}"></span>
      <strong>${esc(a.numero_interne)}</strong><span class="doux">${esc(a.categorie_nom)}</span>${extra}</a>`;

  zone.innerHTML = `
    <div class="titre-page"><h1>Tableau de bord</h1><span class="doux">au ${dateAffichee(auj)}</span></div>
    <div class="tuiles">
      <div class="tuile"><div class="valeur">${parc.length}</div><div class="libelle">Articles au total</div><div class="detail">hors réformés / vendus</div></div>
      <div class="tuile"><div class="valeur">${affectes.length}</div><div class="libelle">Affectés aujourd'hui</div></div>
      <div class="tuile"><div class="valeur ok">${dispo.length}</div><div class="libelle">Disponibles au dépôt</div></div>
      <div class="tuile"><div class="valeur attention">${reparation.length}</div><div class="libelle">En réparation / SAV</div></div>
      <div class="tuile"><div class="valeur">${chf(valeur)}</div><div class="libelle">Valeur du parc</div>
        <div class="detail">${sansPrix ? `${sansPrix} article(s) sans prix renseigné` : "tous les prix sont renseignés"}</div></div>
    </div>
    <div class="deux-colonnes">
      <div class="carte"><h3>Disponibles aujourd'hui (${dispo.length})</h3>
        ${dispo.map((a) => ligneArticle(a)).join("") || '<p class="doux">Aucun article disponible.</p>'}</div>
      <div class="carte"><h3>Fins d'affectation dans les 7 jours (${fins.length})</h3>
        ${fins.map((x) => parId[x.article_id] ? ligneArticle(parId[x.article_id],
          ` — ${esc(libelleChantier(x.chantier_numero, x.chantier_nom, x.responsable || x.chantier_responsable))}
           <span class="doux">jusqu'au ${dateAffichee(x.date_fin)}</span>`) : "").join("") || '<p class="doux">Aucune.</p>'}
        ${reparation.length ? `<h3 style="margin-top:18px">En réparation / SAV</h3>${reparation.map((a) => ligneArticle(a, ` ${`<span class="badge reparation">${esc(STATUTS[a.statut])}</span>`}`)).join("")}` : ""}
      </div>
    </div>`;
}
