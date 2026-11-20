// Outils communs : appels au serveur, dates, montants, couleurs, notifications.

// ---------------------------------------------------------------- Serveur
export async function api(methode, url, corps) {
  const options = { method: methode, headers: {} };
  if (corps instanceof FormData) {
    options.body = corps;
  } else if (corps !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(corps);
  }
  let reponse;
  try {
    reponse = await fetch(url, options);
  } catch {
    throw new Error("Le serveur ne répond pas. L'application est-elle toujours lancée (fenêtre noire ouverte) ?");
  }
  const donnees = await reponse.json().catch(() => ({}));
  if (!reponse.ok) {
    const e = new Error(donnees.erreur || `Erreur ${reponse.status}`);
    e.donnees = donnees;
    e.statut = reponse.status;
    throw e;
  }
  return donnees;
}

// ---------------------------------------------------------------- Texte
export function esc(valeur) {
  return String(valeur ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export function normaliser(texte) {
  return String(texte ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

// ---------------------------------------------------------------- Dates
// Les dates sont stockées au format ISO (2026-10-31) et affichées en JJ.MM.AAAA.
export const JOURS_COURTS = ["dim", "lun", "mar", "mer", "jeu", "ven", "sam"];
export const MOIS = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET",
  "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"];

export function dateAffichee(iso) {
  if (!iso) return "";
  const [a, m, j] = iso.split("-");
  return `${j}.${m}.${a}`;
}

export function isoDepuisDate(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function aujourdhuiIso() {
  return isoDepuisDate(new Date());
}

// Accepte une saisie rapide : « 5.10 », « 5.10.26 », « 05.10.2026 », « 5/10/2026 », « 051026 », « 05102026 ».
// Renvoie la date ISO, « » si vide, ou null si la saisie n'est pas une date valide.
export function lireDate(saisie) {
  let s = String(saisie ?? "").trim();
  if (!s) return "";
  let j, m, a;
  if (/^\d{6}$|^\d{8}$/.test(s)) {
    j = s.slice(0, 2); m = s.slice(2, 4); a = s.slice(4);
  } else if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    [a, m, j] = s.split("-");
  } else {
    const morceaux = s.split(/[.\/\-\s]+/).filter(Boolean);
    if (morceaux.length < 2 || morceaux.length > 3 || morceaux.some((x) => !/^\d+$/.test(x))) return null;
    [j, m, a] = morceaux;
  }
  const annee = a === undefined ? new Date().getFullYear() : (String(a).length <= 2 ? 2000 + Number(a) : Number(a));
  const d = new Date(annee, Number(m) - 1, Number(j));
  if (d.getFullYear() !== annee || d.getMonth() !== Number(m) - 1 || d.getDate() !== Number(j)) return null;
  return isoDepuisDate(d);
}

// Transforme un <input> texte en champ date JJ.MM.AAAA : mise en forme à la sortie du champ.
export function brancherChampDate(input) {
  input.placeholder = "JJ.MM.AAAA";
  input.autocomplete = "off";
  input.addEventListener("blur", () => {
    const iso = lireDate(input.value);
    input.classList.toggle("invalide", iso === null);
    if (iso) input.value = dateAffichee(iso);
  });
}

export function valeurDate(input, nom) {
  const iso = lireDate(input.value);
  if (iso === null) throw new Error(`La date « ${nom} » n'est pas valide (format JJ.MM.AAAA).`);
  return iso;
}

// ---------------------------------------------------------------- Montants
export function chf(montant) {
  if (montant === null || montant === undefined || montant === "") return "";
  const [entier, decimales] = Number(montant).toFixed(2).split(".");
  return `${entier.replace(/\B(?=(\d{3})+(?!\d))/g, "'")}.${decimales} CHF`;
}

export function montantSaisi(montant) {
  if (montant === null || montant === undefined || montant === "") return "";
  return Number(montant).toFixed(2);
}

// ---------------------------------------------------------------- Couleurs
// Les 7 premières couleurs reprennent le cycle de votre Excel actuel.
export const PALETTE = [
  "#F2CEEF", "#C1E4F5", "#FBE2D5", "#C1F0C8", "#FFB7B7", "#FFFFB9", "#CCE0F4",
  "#E2D5F5", "#FFE699", "#D9F2D0", "#F8CBAD", "#D9D9D9",
];

export function couleurParDefaut(nombreArticlesDansCategorie) {
  return PALETTE[nombreArticlesDansCategorie % 7];
}

// Texte noir ou blanc selon la couleur de fond, pour rester lisible.
export function couleurTexte(fond) {
  const h = (fond || "#ffffff").replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? "#1d2733" : "#ffffff";
}

// ---------------------------------------------------------------- Statuts
export const STATUTS = {
  actif: "Actif",
  reparation: "En réparation / SAV",
  perdu: "Perdu / volé",
  reforme: "Réformé / vendu",
};

export function badgeStatut(statut) {
  return `<span class="badge ${esc(statut)}">${esc(STATUTS[statut] || statut)}</span>`;
}

// ---------------------------------------------------------------- Chantiers
export function libelleChantier(numero, nom, responsable) {
  return [numero, nom, responsable].filter((x) => x && String(x).trim()).join(" – ");
}

// ---------------------------------------------------------------- Interface
export function notifier(message, type = "info") {
  const zone = document.getElementById("notifications");
  const div = document.createElement("div");
  div.className = `notification ${type}`;
  div.textContent = message;
  zone.appendChild(div);
  setTimeout(() => div.remove(), type === "erreur" ? 7000 : 3000);
}

export function erreur(e) {
  notifier(e.message || String(e), "erreur");
}

// Fenêtre de confirmation. Renvoie une promesse : true si l'utilisateur confirme.
export function confirmer(message, { titre = "Confirmation", ok = "Confirmer", danger = false } = {}) {
  return new Promise((resoudre) => {
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `
      <div class="contenu">
        <h2>${esc(titre)}</h2>
        <p>${esc(message)}</p>
        <div class="actions">
          <button type="button" data-r="non">Annuler</button>
          <button type="button" data-r="oui" class="${danger ? "danger" : "primaire"}">${esc(ok)}</button>
        </div>
      </div>`;
    document.body.appendChild(dlg);
    dlg.addEventListener("click", (ev) => {
      const r = ev.target.dataset?.r;
      if (r) { dlg.close(); resoudre(r === "oui"); }
    });
    dlg.addEventListener("close", () => { dlg.remove(); resoudre(false); });
    dlg.showModal();
    dlg.querySelector('[data-r="oui"]').focus();
  });
}

// Fenêtre de saisie d'un texte (ex. nom d'une catégorie). Renvoie le texte ou null.
export function demanderTexte(titre, valeur = "", libelle = "Nom") {
  return new Promise((resoudre) => {
    const dlg = document.createElement("dialog");
    dlg.innerHTML = `
      <form method="dialog">
        <h2>${esc(titre)}</h2>
        <label class="champ"><span>${esc(libelle)}</span><input name="v" value="${esc(valeur)}" required></label>
        <div class="actions">
          <button type="button" data-annuler>Annuler</button>
          <button class="primaire">Valider</button>
        </div>
      </form>`;
    document.body.appendChild(dlg);
    let resultat = null;
    dlg.querySelector("form").addEventListener("submit", () => { resultat = dlg.querySelector("input").value.trim() || null; });
    dlg.querySelector("[data-annuler]").addEventListener("click", () => dlg.close());
    dlg.addEventListener("close", () => { dlg.remove(); resoudre(resultat); });
    dlg.showModal();
    dlg.querySelector("input").select();
  });
}

// Tri de tableau : renvoie une fonction de comparaison pour une clé donnée.
export function comparer(cle, sens = 1) {
  return (a, b) => {
    const x = typeof cle === "function" ? cle(a) : a[cle];
    const y = typeof cle === "function" ? cle(b) : b[cle];
    if (x === y) return 0;
    if (x === null || x === undefined || x === "") return 1;
    if (y === null || y === undefined || y === "") return -1;
    if (typeof x === "number" && typeof y === "number") return (x - y) * sens;
    return String(x).localeCompare(String(y), "fr", { numeric: true, sensitivity: "base" }) * sens;
  };
}

// Zone de dépôt de fichiers : clic pour choisir, ou glisser-déposer.
export function zoneDepot(element, multiple, accept, surFichiers) {
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = multiple;
  if (accept) input.accept = accept;
  input.hidden = true;
  element.appendChild(input);
  element.addEventListener("click", (e) => { if (!e.target.closest("button, a")) input.click(); });
  input.addEventListener("change", () => { if (input.files.length) surFichiers([...input.files]); });
  element.addEventListener("dragover", (e) => { e.preventDefault(); element.classList.add("survol"); });
  element.addEventListener("dragleave", () => element.classList.remove("survol"));
  element.addEventListener("drop", (e) => {
    e.preventDefault();
    element.classList.remove("survol");
    if (e.dataTransfer.files.length) surFichiers([...e.dataTransfer.files]);
  });
}

