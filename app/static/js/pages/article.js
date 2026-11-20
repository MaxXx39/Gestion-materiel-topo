// Fiche article : création, modification, duplication, photo, documents, historique.
import {
  api, esc, notifier, erreur, confirmer, demanderTexte, brancherChampDate, valeurDate, dateAffichee,
  montantSaisi, PALETTE, couleurParDefaut, STATUTS, libelleChantier, zoneDepot,
} from "../outils.js";

const CHAMPS_TEXTE = ["numero_interne", "designation", "code_compta", "marque", "modele", "numero_serie", "fournisseur", "notes"];

export default async function pageArticle(zone, [ident], params) {
  const nouveau = !ident || ident === "nouveau";
  let categories = await api("GET", "/api/categories");
  let article;
  if (!nouveau) {
    article = await api("GET", `/api/articles/${ident}`);
  } else if (params.get("copie")) {
    // Duplication : on reprend tout sauf ce qui est propre à l'appareil.
    const source = await api("GET", `/api/articles/${params.get("copie")}`);
    const cat = categories.find((c) => c.id === source.categorie_id);
    article = { ...source, id: null, numero_interne: "", numero_serie: "", date_achat: null, photo: null, notes: "",
      statut: "actif", couleur: couleurParDefaut(cat?.nb_articles || 0) };
  } else {
    const cat = categories.find((c) => String(c.id) === params.get("cat")) || categories[0];
    article = { categorie_id: cat?.id, couleur: couleurParDefaut(cat?.nb_articles || 0), statut: "actif" };
  }
  const existe = !!article.id;
  let couleurTouchee = existe;

  zone.innerHTML = `
    <div class="titre-page">
      <a class="bouton" href="#/parc">◀ Parc</a>
      <h1>${existe ? esc(article.numero_interne) : (params.get("copie") ? "Copie de matériel" : "Nouveau matériel")}</h1>
      ${existe ? badgeLieu(article) : ""}
    </div>
    <form id="fiche" autocomplete="off">
      <div class="grille-fiche">
        <div class="colonne">
          <div class="carte">
            <div class="champs">
              <label class="champ"><span>Catégorie <b class="obligatoire">*</b></span>
                <div class="ligne-champ"><select name="categorie_id" required></select>
                <button type="button" id="nouvelle-cat" title="Créer une catégorie">＋</button></div></label>
              <label class="champ"><span>Statut</span>
                <select name="statut">${Object.entries(STATUTS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("")}</select>
                <small>Les articles non actifs sont masqués du planning, leur historique est conservé.</small></label>
              <label class="champ"><span>N° interne <b class="obligatoire">*</b> (affiché sur le planning et le PDF)</span>
                <input name="numero_interne" required placeholder="ex. 953A11"></label>
              <label class="champ"><span>Code article compta (N° MS – à facturer)</span>
                <input name="code_compta" placeholder="ex. 112"></label>
              <label class="champ large"><span>Désignation</span>
                <input name="designation" placeholder="ex. Canne GPS Leica GS18 T"></label>
              <div class="champ large"><span>Couleur sur le planning et le PDF</span>
                <div class="palette" id="palette">
                  ${PALETTE.map((c) => `<button type="button" class="pastille" data-c="${c}" style="background:${c}" title="${c}"></button>`).join("")}
                  <input type="color" name="couleur" title="Autre couleur">
                  <span class="apercu-ligne" id="apercu"><span class="code"></span><span class="nom"></span></span>
                </div></div>
            </div>
          </div>
          <div class="carte">
            <div class="champs">
              <label class="champ"><span>Marque</span><input name="marque"></label>
              <label class="champ"><span>Modèle</span><input name="modele"></label>
              <label class="champ"><span>N° de série</span><input name="numero_serie"></label>
              <label class="champ"><span>Fournisseur</span><input name="fournisseur"></label>
              <label class="champ"><span>Date d'achat</span><input name="date_achat" class="date"></label>
              <label class="champ"><span>Prix (CHF)</span><input name="prix_chf" inputmode="decimal" placeholder="0.00"></label>
              <label class="champ"><span>Fin de garantie</span><input name="fin_garantie" class="date"></label>
              <span></span>
              <label class="champ large"><span>Notes</span><textarea name="notes"></textarea></label>
            </div>
          </div>
        </div>
        <div class="colonne">
          <div class="carte"><h3>Photo</h3><div id="photo"></div></div>
          <div class="carte"><h3>Documents</h3><div id="documents"></div></div>
          <div class="carte"><h3>Historique des affectations</h3><div id="historique"></div></div>
          <div class="carte"><h3>Accessoires</h3><p class="doux">Batteries, trépied… : prévu dans une prochaine étape.</p></div>
        </div>
      </div>
      <div class="actions barre-actions">
        <button class="primaire" type="submit">Enregistrer</button>
        <button type="button" id="enregistrer-autre">Enregistrer et ajouter un autre</button>
        ${existe ? `<button type="button" id="dupliquer">Dupliquer</button>` : ""}
        <span class="espace"></span>
        ${existe ? `<button type="button" class="danger" id="supprimer">Supprimer</button>` : ""}
      </div>
    </form>`;

  const form = zone.querySelector("#fiche");
  const champ = (nom) => form.elements[nom];

  // ---- Remplissage
  function remplirCategories(selection) {
    champ("categorie_id").innerHTML = categories.length
      ? categories.map((c) => `<option value="${c.id}">${esc(c.nom)}</option>`).join("")
      : `<option value="">— créez d'abord une catégorie avec ＋ —</option>`;
    if (selection) champ("categorie_id").value = selection;
  }
  remplirCategories(article.categorie_id);
  champ("statut").value = article.statut || "actif";
  for (const nom of CHAMPS_TEXTE) champ(nom).value = article[nom] || "";
  champ("prix_chf").value = montantSaisi(article.prix_chf);
  champ("date_achat").value = dateAffichee(article.date_achat);
  champ("fin_garantie").value = dateAffichee(article.fin_garantie);
  form.querySelectorAll("input.date").forEach(brancherChampDate);
  choisirCouleur(article.couleur || PALETTE[0]);

  // ---- Couleur
  function choisirCouleur(c) {
    champ("couleur").value = c.toLowerCase();
    form.querySelectorAll(".pastille").forEach((p) => p.classList.toggle("choisie", p.dataset.c.toLowerCase() === c.toLowerCase()));
    majApercu();
  }
  function majApercu() {
    const ap = zone.querySelector("#apercu");
    ap.querySelector(".code").textContent = champ("code_compta").value || " ";
    ap.querySelector(".nom").textContent = champ("numero_interne").value || "N° interne";
    ap.querySelector(".nom").style.background = champ("couleur").value;
  }
  zone.querySelector("#palette").addEventListener("click", (e) => {
    const p = e.target.closest(".pastille");
    if (p) { couleurTouchee = true; choisirCouleur(p.dataset.c); }
  });
  champ("couleur").addEventListener("input", () => { couleurTouchee = true; choisirCouleur(champ("couleur").value); });
  champ("numero_interne").addEventListener("input", majApercu);
  champ("code_compta").addEventListener("input", majApercu);
  champ("categorie_id").addEventListener("change", () => {
    if (couleurTouchee) return;
    const cat = categories.find((c) => String(c.id) === champ("categorie_id").value);
    choisirCouleur(couleurParDefaut(cat?.nb_articles || 0));
  });

  zone.querySelector("#nouvelle-cat").onclick = async () => {
    const nom = await demanderTexte("Nouvelle catégorie", "", "Nom de la catégorie");
    if (!nom) return;
    try {
      const cat = await api("POST", "/api/categories", { nom });
      categories = await api("GET", "/api/categories");
      remplirCategories(cat.id);
      champ("categorie_id").dispatchEvent(new Event("change"));
      notifier(`Catégorie « ${cat.nom} » créée.`);
    } catch (e) { erreur(e); }
  };

  // ---- Enregistrement
  async function enregistrer() {
    const donnees = { couleur: champ("couleur").value.toUpperCase() };
    for (const nom of CHAMPS_TEXTE) donnees[nom] = champ(nom).value;
    donnees.categorie_id = champ("categorie_id").value;
    donnees.statut = champ("statut").value;
    donnees.prix_chf = champ("prix_chf").value;
    donnees.date_achat = valeurDate(champ("date_achat"), "Date d'achat");
    donnees.fin_garantie = valeurDate(champ("fin_garantie"), "Fin de garantie");
    donnees.parent_id = article.parent_id || null;
    if (existe) {
      await api("PUT", `/api/articles/${article.id}`, donnees);
      return article.id;
    }
    return (await api("POST", "/api/articles", donnees)).id;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const id = await enregistrer();
      notifier("Article enregistré.");
      if (existe) location.hash = "#/parc";
      else location.hash = `#/article/${id}`; // on reste sur la fiche pour ajouter photo et documents
    } catch (err) { erreur(err); }
  });
  zone.querySelector("#enregistrer-autre").onclick = async () => {
    if (!form.reportValidity()) return;
    try {
      await enregistrer();
      notifier("Article enregistré. Saisissez le suivant.");
      const cible = `#/article/nouveau?cat=${champ("categorie_id").value}`;
      if (location.hash === cible) window.dispatchEvent(new HashChangeEvent("hashchange"));
      else location.hash = cible;
    } catch (err) { erreur(err); }
  };
  if (existe) {
    zone.querySelector("#dupliquer").onclick = () => { location.hash = `#/article/nouveau?copie=${article.id}`; };
    zone.querySelector("#supprimer").onclick = async () => {
      const ok = await confirmer(`Supprimer définitivement « ${article.numero_interne} », sa photo et ses documents ?`,
        { titre: "Supprimer l'article", ok: "Supprimer", danger: true });
      if (!ok) return;
      try {
        await api("DELETE", `/api/articles/${article.id}`);
        notifier("Article supprimé.");
        location.hash = "#/parc";
      } catch (err) { erreur(err); }
    };
  }

  // ---- Photo, documents, historique
  dessinerPhoto(zone.querySelector("#photo"), article);
  dessinerDocuments(zone.querySelector("#documents"), article);
  dessinerHistorique(zone.querySelector("#historique"), article);
  if (!existe) champ("numero_interne").focus();
}

function badgeLieu(a) {
  if (a.aujourdhui) {
    const x = a.aujourdhui;
    return `<span class="badge">Aujourd'hui : ${esc(libelleChantier(x.chantier_numero, x.chantier_nom, x.responsable))}</span>`;
  }
  return a.statut === "actif" ? `<span class="badge actif">Disponible aujourd'hui</span>` : "";
}

function dessinerPhoto(conteneur, article) {
  if (!article.id) {
    conteneur.innerHTML = `<p class="doux">Enregistrez l'article pour pouvoir ajouter une photo.</p>`;
    return;
  }
  conteneur.innerHTML = `
    <div class="photo" title="Cliquez ou glissez une image ici">
      ${article.photo ? `<img src="/fichiers/photos/${esc(article.photo)}" alt="Photo">` : "Glissez une photo ici<br>ou cliquez pour en choisir une"}
    </div>
    ${article.photo ? `<div class="actions" style="margin-top:8px"><button type="button" class="danger" id="sup-photo">Retirer la photo</button></div>` : ""}`;
  zoneDepot(conteneur.querySelector(".photo"), false, "image/*", async ([fichier]) => {
    const fd = new FormData();
    fd.append("fichier", fichier);
    try {
      const r = await api("POST", `/api/articles/${article.id}/photo`, fd);
      article.photo = r.photo;
      dessinerPhoto(conteneur, article);
      notifier("Photo enregistrée.");
    } catch (e) { erreur(e); }
  });
  const sup = conteneur.querySelector("#sup-photo");
  if (sup) sup.onclick = async () => {
    if (!(await confirmer("Retirer la photo de cet article ?", { ok: "Retirer", danger: true }))) return;
    try {
      await api("DELETE", `/api/articles/${article.id}/photo`);
      article.photo = null;
      dessinerPhoto(conteneur, article);
    } catch (e) { erreur(e); }
  };
}

function dessinerDocuments(conteneur, article) {
  if (!article.id) {
    conteneur.innerHTML = `<p class="doux">Enregistrez l'article pour pouvoir joindre des documents.</p>`;
    return;
  }
  const docs = article.documents || [];
  conteneur.innerHTML = `
    ${docs.length ? `<ul class="documents">${docs.map((d) => `
      <li><a href="/api/documents/${d.id}" target="_blank" title="Ouvrir">${esc(d.nom_original)}</a>
      <button type="button" class="lien" data-sup="${d.id}" title="Supprimer ce document">✕</button></li>`).join("")}</ul>`
      : `<p class="doux">Aucun document.</p>`}
    <div class="zone-depot">Glissez ici notice, certificat, facture…<br>ou cliquez pour choisir</div>`;
  zoneDepot(conteneur.querySelector(".zone-depot"), true, "", async (fichiers) => {
    const fd = new FormData();
    fichiers.forEach((f) => fd.append("fichiers", f));
    try {
      await api("POST", `/api/articles/${article.id}/documents`, fd);
      article.documents = (await api("GET", `/api/articles/${article.id}`)).documents;
      dessinerDocuments(conteneur, article);
      notifier(fichiers.length > 1 ? `${fichiers.length} documents ajoutés.` : "Document ajouté.");
    } catch (e) { erreur(e); }
  });
  conteneur.querySelectorAll("[data-sup]").forEach((b) => {
    b.onclick = async () => {
      const doc = docs.find((d) => String(d.id) === b.dataset.sup);
      if (!(await confirmer(`Supprimer le document « ${doc.nom_original} » ?`, { ok: "Supprimer", danger: true }))) return;
      try {
        await api("DELETE", `/api/documents/${doc.id}`);
        article.documents = docs.filter((d) => d !== doc);
        dessinerDocuments(conteneur, article);
      } catch (e) { erreur(e); }
    };
  });
}

function dessinerHistorique(conteneur, article) {
  const h = article.historique || [];
  conteneur.innerHTML = h.length
    ? `<table class="liste"><tbody>${h.map((x) => `<tr>
        <td style="white-space:nowrap">${dateAffichee(x.date_debut)} → ${dateAffichee(x.date_fin)}</td>
        <td>${esc(libelleChantier(x.chantier_numero, x.chantier_nom, x.responsable))}</td></tr>`).join("")}</tbody></table>`
    : `<p class="doux">Aucune affectation pour le moment.</p>`;
}
