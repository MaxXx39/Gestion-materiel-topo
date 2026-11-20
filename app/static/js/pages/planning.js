// Planning : vue mois (glisser pour créer, étirer, déplacer, cliquer pour modifier) et vue année.
import {
  api, esc, notifier, erreur, confirmer, dateAffichee, lireDate, aujourdhuiIso, JOURS_COURTS, MOIS,
  libelleChantier, normaliser, couleurTexte, STATUTS,
} from "../outils.js";

const MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];

// État conservé quand on change de page puis qu'on revient.
const etat = { annee: null, mois: null, mode: "mois", inactifs: false, reperer: "" };
let D = { articles: [], chantiers: [], affectations: [], annulable: false };
let zonePage = null;

// ------------------------------------------------------------------ Dates
const dte = (iso) => new Date(iso + "T00:00:00Z");
const iso = (d) => d.toISOString().slice(0, 10);
const plus = (s, n) => { const d = dte(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
const nbJours = (a, m) => new Date(Date.UTC(a, m + 1, 0)).getUTCDate();
const jourDe = (a, m, j) => iso(new Date(Date.UTC(a, m, j)));
const duree = (d, f) => Math.round((dte(f) - dte(d)) / 864e5) + 1;
const jj = dateAffichee;

// ------------------------------------------------------------------ Données
const chantier = (id) => D.chantiers.find((c) => c.id === id);
const article = (id) => D.articles.find((a) => a.id === id);
const responsable = (af) => af.responsable || af.chantier_responsable || "";
const libelle = (af) => libelleChantier(af.chantier_numero, af.chantier_nom, responsable(af));
const libelleCh = (c) => libelleChantier(c.numero, c.nom, c.responsable);
const visibles = () => D.articles.filter((a) => etat.inactifs || a.statut === "actif");

function periode() {
  if (etat.mode === "annee") return [`${etat.annee}-01-01`, `${etat.annee}-12-31`];
  return [jourDe(etat.annee, etat.mois, 1), jourDe(etat.annee, etat.mois, nbJours(etat.annee, etat.mois))];
}

async function charger() {
  const [debut, fin] = periode();
  const [articles, chantiers, aff] = await Promise.all([
    api("GET", "/api/articles"), api("GET", "/api/chantiers"),
    api("GET", `/api/affectations?debut=${debut}&fin=${fin}`),
  ]);
  D = { articles, chantiers, affectations: aff.affectations, annulable: aff.annulable };
}

async function rafraichir() {
  try { await charger(); } catch (e) { erreur(e); }
  dessiner();
}

function groupes(liste) {
  const res = [];
  for (const a of liste) {
    const dernier = res[res.length - 1];
    if (dernier && dernier.id === a.categorie_id) dernier.articles.push(a);
    else res.push({ id: a.categorie_id, nom: a.categorie_nom, articles: [a] });
  }
  return res;
}

// ------------------------------------------------------------------ Page
export default async function pagePlanning(zone, args) {
  zonePage = zone;
  const auj = aujourdhuiIso();
  if (args[0] && args[1]) {
    etat.annee = Number(args[0]); etat.mois = Number(args[1]) - 1; etat.mode = "mois";
  } else if (etat.annee === null) {
    etat.annee = Number(auj.slice(0, 4)); etat.mois = Number(auj.slice(5, 7)) - 1;
  }
  await charger();
  dessiner();
}

function dessiner() {
  const zone = zonePage;
  if (!zone || !zone.isConnected) return;
  const auj = aujourdhuiIso();
  const dispo = D.articles.filter((a) => a.statut === "actif" && !a.aujourdhui).length;
  zone.innerHTML = `
    <div class="barre-planning">
      <button data-act="prec" title="Précédent">◀</button>
      <h1>${etat.mode === "mois" ? `${MOIS[etat.mois]} ${etat.annee}` : `Année ${etat.annee}`}</h1>
      <button data-act="suiv" title="Suivant">▶</button>
      <button data-act="auj">Aujourd'hui</button>
      <span class="seg"><button data-act="mois" class="${etat.mode === "mois" ? "actif" : ""}">Mois</button><button data-act="annee" class="${etat.mode === "annee" ? "actif" : ""}">Année</button></span>
      <label class="case"><input type="checkbox" data-act="inactifs" ${etat.inactifs ? "checked" : ""}> Inactifs</label>
      <span class="espace"></span>
      <span class="compteur" title="Articles actifs disponibles au dépôt aujourd'hui">Dispo : <b>${dispo}</b></span>
      <input type="search" id="reperer" placeholder="Repérer un chantier, un article…" value="${esc(etat.reperer)}">
      <button data-act="annuler" ${D.annulable ? "" : "disabled"} title="Annuler la dernière modification (Ctrl+Z)">↶ Annuler</button>
      <button data-act="clavier" title="Saisie précise au clavier">＋ Saisie</button>
      <button class="primaire" data-act="exporter" ${etat.mode === "mois" ? "" : "disabled title=\"Choisissez un mois\""}>Exporter le mois</button>
    </div>
    ${!D.articles.length ? `<div class="carte message-attente">Aucun article. Commencez par <a href="#/preremplir">importer depuis l'Excel</a> ou <a href="#/article/nouveau">ajouter un matériel</a>.</div>`
      : etat.mode === "mois" ? grilleMois(auj) : grilleAnnee(auj)}
    <div class="legende" ${etat.mode === "annee" ? "hidden" : ""}>
      <span><b>Glisser</b> sur les jours d'une ligne = nouvelle affectation</span>
      <span><b>Tirer le bord</b> d'une barre = allonger / raccourcir</span>
      <span><b>Glisser</b> une barre = la déplacer</span>
      <span><b>Cliquer</b> sur une barre = modifier, rendre, changer de chantier</span>
      <span><i style="border-right:3px dashed #555"></i> continue sur le mois voisin</span>
      <span><i class="nf" style="background-image:repeating-linear-gradient(45deg,transparent 0 6px,rgba(255,255,255,.6) 6px 9px)"></i> chantier non facturable</span>
    </div>
    <div id="bulle"></div>`;

  zone.querySelector(".barre-planning").addEventListener("click", actionBarre);
  zone.querySelector('[data-act="inactifs"]').addEventListener("change", (e) => { etat.inactifs = e.target.checked; dessiner(); });
  const rep = zone.querySelector("#reperer");
  rep.addEventListener("input", () => { etat.reperer = rep.value; appliquerReperage(); });
  if (etat.mode === "mois") brancherSouris();
  else zone.querySelectorAll(".an-mois [data-m]").forEach((x) => {
    x.onclick = () => { etat.mois = Number(x.dataset.m); etat.mode = "mois"; rafraichir(); };
  });
  appliquerReperage();
}

async function actionBarre(e) {
  const b = e.target.closest("button[data-act]");
  if (!b) return;
  const auj = aujourdhuiIso();
  switch (b.dataset.act) {
    case "prec": case "suiv": {
      const n = b.dataset.act === "prec" ? -1 : 1;
      if (etat.mode === "annee") etat.annee += n;
      else { etat.mois += n; if (etat.mois < 0) { etat.mois = 11; etat.annee--; } if (etat.mois > 11) { etat.mois = 0; etat.annee++; } }
      return rafraichir();
    }
    case "auj": etat.annee = Number(auj.slice(0, 4)); etat.mois = Number(auj.slice(5, 7)) - 1; etat.mode = "mois"; return rafraichir();
    case "mois": etat.mode = "mois"; return rafraichir();
    case "annee": etat.mode = "annee"; return rafraichir();
    case "annuler": return annuler();
    case "clavier": return fenetreCreation();
    case "exporter": return fenetreExport();
    default:
  }
}

async function annuler() {
  try { await api("POST", "/api/annuler"); notifier("Dernière modification annulée."); } catch (e) { erreur(e); }
  rafraichir();
}

document.addEventListener("keydown", (e) => {
  if (!location.hash.startsWith("#/planning") || document.querySelector("dialog[open]")) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !e.target.closest("input, textarea")) {
    e.preventDefault();
    if (D.annulable) annuler();
  }
});

function appliquerReperage() {
  const q = normaliser(etat.reperer).trim();
  zonePage.querySelectorAll(".pl-ligne").forEach((l) => {
    const a = article(Number(l.dataset.art));
    const trouve = !!q && normaliser(a.numero_interne).includes(q);
    l.classList.toggle("trouve", trouve);
    l.querySelectorAll(".barre").forEach((b) => b.classList.toggle("pale", !!q && !trouve && !normaliser(b.textContent).includes(q)));
  });
}

// ------------------------------------------------------------------ Grilles
function grilleMois(auj) {
  const { annee, mois } = etat;
  const n = nbJours(annee, mois);
  const debut = jourDe(annee, mois, 1), fin = jourDe(annee, mois, n);
  const cols = `62px 160px repeat(${n}, minmax(24px, 1fr))`;
  const jours = Array.from({ length: n }, (_, i) => {
    const s = jourDe(annee, mois, i + 1), w = dte(s).getUTCDay();
    return { s, j: i + 1, w, cls: `${s === auj ? "auj" : ""} ${w === 1 ? "lundi" : ""} ${w === 0 || w === 6 ? "we" : ""}` };
  });
  let h = `<div class="planning"><div class="pl-tete" style="grid-template-columns:34px ${cols}"><div></div>
    <div class="h">Code compta</div><div class="h">N° interne</div>
    ${jours.map((x) => `<div class="j ${x.cls}"><b>${x.j}</b>${JOURS_COURTS[x.w]}</div>`).join("")}</div>`;
  for (const g of groupes(visibles())) {
    h += `<div class="pl-groupe"><div class="pl-cat"><span>${esc(g.nom)}</span></div><div class="pl-lignes">`;
    for (const a of g.articles) {
      h += `<div class="pl-ligne ${a.statut !== "actif" ? "inactif" : ""}" style="grid-template-columns:${cols}" data-art="${a.id}">
        <div class="code" style="grid-column:1">${esc(a.code_compta)}</div>
        <a class="num" href="#/article/${a.id}" style="grid-column:2;background:${esc(a.couleur)};color:${couleurTexte(a.couleur)}" title="Ouvrir la fiche">${esc(a.numero_interne)}${a.statut !== "actif" ? `<small>(${esc(STATUTS[a.statut])})</small>` : ""}</a>
        ${jours.map((x) => `<div class="c ${x.cls}" style="grid-column:${x.j + 2}" data-j="${x.j}"></div>`).join("")}`;
      for (const af of D.affectations.filter((x) => x.article_id === a.id && x.date_fin >= debut && x.date_debut <= fin)) {
        const j1 = af.date_debut < debut ? 1 : Number(af.date_debut.slice(8));
        const j2 = af.date_fin > fin ? n : Number(af.date_fin.slice(8));
        const txt = libelle(af);
        h += `<div class="barre ${af.date_debut < debut ? "suite-g" : ""} ${af.date_fin > fin ? "suite-d" : ""} ${af.chantier_facturable ? "" : "nf"}"
          style="grid-column:${j1 + 2}/${j2 + 3};background:${esc(a.couleur)};border-color:${fonce(a.couleur)};color:${couleurTexte(a.couleur)}"
          data-aff="${af.id}" title="${esc(txt)}&#10;${jj(af.date_debut)} → ${jj(af.date_fin)} (${duree(af.date_debut, af.date_fin)} j)${af.remarque ? "&#10;" + esc(af.remarque) : ""}">${af.date_debut >= debut ? '<span class="pg"></span>' : ""}${esc(txt)}${af.date_fin <= fin ? '<span class="pd"></span>' : ""}</div>`;
      }
      h += `</div>`;
    }
    h += `</div></div>`;
  }
  return h + `</div>`;
}

function grilleAnnee(auj) {
  const a0 = Date.UTC(etat.annee, 0, 1), px = 3;
  const total = (Date.UTC(etat.annee + 1, 0, 1) - a0) / 864e5;
  let h = `<div class="annee"><div class="an-mois">${MOIS_COURTS.map((m, i) =>
    `<div data-m="${i}" style="width:${nbJours(etat.annee, i) * px}px" title="Ouvrir ${MOIS[i].toLowerCase()}">${m}</div>`).join("")}</div>`;
  const t = (dte(auj) - a0) / 864e5;
  for (const g of groupes(visibles())) {
    h += `<div class="an-sep"></div>`;
    for (const a of g.articles) {
      h += `<div class="an-ligne"><div class="n" title="${esc(g.nom)}">${esc(a.numero_interne)}</div><div class="an-piste" style="width:${total * px}px">`;
      for (const af of D.affectations.filter((x) => x.article_id === a.id)) {
        const d = Math.max(0, (dte(af.date_debut) - a0) / 864e5), f = Math.min(total, (dte(af.date_fin) - a0) / 864e5 + 1);
        h += `<i style="left:${d * px}px;width:${(f - d) * px}px;background:${esc(a.couleur)}" title="${esc(libelle(af))} : ${jj(af.date_debut)} → ${jj(af.date_fin)}"></i>`;
      }
      if (t >= 0 && t < total) h += `<i style="left:${t * px}px;width:2px;background:var(--accent);border:none"></i>`;
      h += `</div></div>`;
    }
  }
  return h + `</div><p class="doux">Cliquez sur un mois pour l'ouvrir.</p>`;
}

function fonce(hex) {
  const n = parseInt(hex.slice(1), 16);
  const f = (v) => Math.round(v * 0.62).toString(16).padStart(2, "0");
  return "#" + f(n >> 16) + f((n >> 8) & 255) + f(n & 255);
}

// ------------------------------------------------------------------ Souris : créer, étirer, déplacer
function brancherSouris() {
  const zone = zonePage;
  const n = nbJours(etat.annee, etat.mois);
  const debutMois = jourDe(etat.annee, etat.mois, 1), finMois = jourDe(etat.annee, etat.mois, n);
  const bulle = zone.querySelector("#bulle");
  let selection = null, op = null;

  const jourSous = (ligne, x) => {
    const r = ligne.querySelector('.c[data-j="1"]').getBoundingClientRect();
    return Math.min(n, Math.max(1, Math.floor((x - r.left) / r.width) + 1));
  };
  const montrerBulle = (e, d, f) => {
    bulle.style.display = "block";
    bulle.style.left = `${e.clientX + 14}px`;
    bulle.style.top = `${e.clientY + 16}px`;
    bulle.textContent = `${jj(d)} → ${jj(f)} · ${duree(d, f)} j`;
  };
  const marquer = () => selection.ligne.querySelectorAll(".c").forEach((c) => {
    const j = Number(c.dataset.j);
    c.classList.toggle("sel", j >= Math.min(selection.j0, selection.j1) && j <= Math.max(selection.j0, selection.j1));
  });

  zone.querySelectorAll(".pl-ligne").forEach((ligne) => {
    ligne.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return;
      const b = e.target.closest(".barre");
      if (b) {
        const af = D.affectations.find((x) => x.id === Number(b.dataset.aff));
        const mode = e.target.classList.contains("pg") ? "g" : e.target.classList.contains("pd") ? "d" : "deplacer";
        op = { b, af, mode, ligne, jDep: jourSous(ligne, e.clientX), d: af.date_debut, f: af.date_fin, bouge: false };
        e.preventDefault();
        return;
      }
      const c = e.target.closest(".c");
      if (!c) return;
      selection = { ligne, j0: Number(c.dataset.j), j1: Number(c.dataset.j) };
      marquer();
      e.preventDefault();
    });
  });

  window.onmousemove = (e) => {
    if (selection) {
      selection.j1 = jourSous(selection.ligne, e.clientX);
      marquer();
      montrerBulle(e, jourDe(etat.annee, etat.mois, Math.min(selection.j0, selection.j1)), jourDe(etat.annee, etat.mois, Math.max(selection.j0, selection.j1)));
      return;
    }
    if (!op) return;
    const delta = jourSous(op.ligne, e.clientX) - op.jDep;
    if (delta !== 0) op.bouge = true;
    if (!op.bouge) return;
    let d = op.af.date_debut, f = op.af.date_fin;
    if (op.mode === "g") { d = plus(op.af.date_debut, delta); if (d > f) d = f; }
    if (op.mode === "d") { f = plus(op.af.date_fin, delta); if (f < d) f = d; }
    if (op.mode === "deplacer") { d = plus(op.af.date_debut, delta); f = plus(op.af.date_fin, delta); }
    op.d = d; op.f = f;
    const a1 = d < debutMois ? 1 : d > finMois ? n : Number(d.slice(8));
    const a2 = f > finMois ? n : f < debutMois ? 1 : Number(f.slice(8));
    op.b.style.gridColumn = `${a1 + 2}/${a2 + 3}`;
    op.b.classList.add("glisse");
    montrerBulle(e, d, f);
  };

  window.onmouseup = () => {
    if (!zone.isConnected) return;
    bulle.style.display = "none";
    if (op) {
      const o = op; op = null;
      if (!o.bouge) { fenetreModification(o.af); return; }
      if (o.d === o.af.date_debut && o.f === o.af.date_fin) { dessiner(); return; }
      enregistrer("PUT", `/api/affectations/${o.af.id}`, { ...corpsDe(o.af), date_debut: o.d, date_fin: o.f });
      return;
    }
    if (selection) {
      const s = selection; selection = null;
      const d = jourDe(etat.annee, etat.mois, Math.min(s.j0, s.j1)), f = jourDe(etat.annee, etat.mois, Math.max(s.j0, s.j1));
      fenetreCreation(Number(s.ligne.dataset.art), d, f, () => s.ligne.querySelectorAll(".sel").forEach((c) => c.classList.remove("sel")));
    }
  };
}

const corpsDe = (af) => ({
  article_id: af.article_id, chantier_id: af.chantier_id, date_debut: af.date_debut, date_fin: af.date_fin,
  responsable: af.responsable, remarque: af.remarque,
});

// Envoie une création / modification ; en cas de chevauchement, demande quoi faire.
async function enregistrer(methode, url, corps) {
  try {
    await api(methode, url, corps);
  } catch (e) {
    if (e.donnees?.chevauchement) {
      const mode = await fenetreChevauchement(corps, e.donnees.conflits);
      if (mode) {
        try { await api(methode, url, { ...corps, conflit: mode }); } catch (e2) { erreur(e2); }
      }
    } else {
      erreur(e);
    }
  }
  await rafraichir();
}

// ------------------------------------------------------------------ Export du mois (PDF + Excel)
function fenetreExport() {
  const nom = `${etat.annee}_${String(etat.mois + 1).padStart(2, "0")}`;
  const base = `/api/export/mois/${etat.annee}/${etat.mois + 1}`;
  const dlg = fenetre(`
    <h2>Exporter ${MOIS[etat.mois].toLowerCase()} ${etat.annee}</h2>
    <p class="sous">Le PDF est pour la compta. L'Excel, avec la même mise en page, permet à quelqu'un de modifier
    le tableau en votre absence (il n'est pas réimporté dans l'application).</p>
    <div class="export-choix">
      <a class="bouton primaire-lien" href="#" data-les-deux>⬇ Télécharger les deux <small>${nom}.pdf + ${nom}.xlsx</small></a>
      <a class="bouton" href="${base}.pdf" download="${nom}.pdf">⬇ PDF pour la compta <small>${nom}.pdf</small></a>
      <a class="bouton" href="${base}.xlsx" download="${nom}.xlsx">⬇ Excel modifiable <small>${nom}.xlsx</small></a>
      <a class="bouton" href="${base}.pdf?voir=1" target="_blank">👁 Aperçu du PDF dans un nouvel onglet</a>
    </div>
    <div class="actions"><button data-fermer>Fermer</button></div>`);
  dlg.querySelector("[data-fermer]").onclick = () => dlg.close();
  dlg.querySelector("[data-les-deux]").onclick = (e) => {
    e.preventDefault();
    for (const [i, ext] of ["pdf", "xlsx"].entries()) {
      setTimeout(() => {
        const a = document.createElement("a");
        a.href = `${base}.${ext}`;
        a.download = `${nom}.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }, i * 600);
    }
    notifier(`${nom}.pdf et ${nom}.xlsx téléchargés (dossier Téléchargements).`);
  };
}

// ------------------------------------------------------------------ Fenêtres
function fenetre(html) {
  const dlg = document.createElement("dialog");
  dlg.innerHTML = `<div class="contenu">${html}</div>`;
  document.body.appendChild(dlg);
  dlg.addEventListener("close", () => dlg.remove());
  dlg.showModal();
  return dlg;
}

function fenetreChevauchement(corps, conflits) {
  return new Promise((resoudre) => {
    const a = article(corps.article_id);
    const dlg = fenetre(`
      <h2>Chevauchement</h2>
      <p class="sous">${esc(a?.numero_interne)} est déjà affecté sur cette période :<br>
      ${conflits.map((x) => `• ${esc(libelle(x))} (${jj(x.date_debut)} → ${jj(x.date_fin)})`).join("<br>")}</p>
      <div class="choix">
        <button data-r="couper"><b>Couper l'existante</b><small>Garder l'ancienne affectation avant et après la nouvelle période (raccourcie ou coupée en deux).</small></button>
        <button data-r="remplacer"><b>Remplacer</b><small>Supprimer entièrement l'ancienne affectation.</small></button>
        <button data-r=""><b>Annuler</b><small>Ne rien changer.</small></button>
      </div>`);
    let r = "";
    dlg.addEventListener("click", (e) => { const b = e.target.closest("button[data-r]"); if (b) { r = b.dataset.r; dlg.close(); } });
    dlg.addEventListener("close", () => resoudre(r));
  });
}

const BLOC_CHANTIER = `
  <label class="champ"><span>Chantier</span><input class="rch" placeholder="Tapez un n° ou un nom de chantier…" autocomplete="off"></label>
  <div class="liste-ch"></div>
  <div class="nouveau rapide" hidden><h3>Nouveau chantier</h3>
    <div class="deux"><label class="champ"><span>N° de chantier</span><input name="numero"></label>
    <label class="champ"><span>Nom</span><input name="nom"></label></div>
    <div class="deux"><label class="champ"><span>Responsable (facultatif)</span><input name="resp"></label>
    <div class="champ"><span>&nbsp;</span><label class="case"><input type="checkbox" name="fact" checked> Facturable</label></div></div>
  </div>`;

// Sélecteur de chantier : recherche + création à la volée. Renvoie une fonction async qui donne l'id choisi.
function selecteurChantier(dlg, idInitial, surChoix) {
  const inp = dlg.querySelector(".rch"), liste = dlg.querySelector(".liste-ch"), nv = dlg.querySelector(".nouveau");
  let choisi = idInitial || null;
  if (idInitial) inp.value = libelleCh(chantier(idInitial));
  const maj = () => {
    const q = normaliser(inp.value).replace(/\s/g, "");
    const res = D.chantiers.filter((c) => (!c.archive || c.id === choisi) && normaliser(libelleCh(c)).replace(/\s/g, "").includes(q)).slice(0, 40);
    const exact = res.some((c) => libelleCh(c) === inp.value.trim());
    liste.innerHTML = res.map((c) => `<div data-c="${c.id}" class="${c.id === choisi ? "choisi" : ""}">${esc(libelleCh(c))}${c.facturable ? "" : " <small>(non facturable)</small>"}</div>`).join("")
      + (inp.value.trim() && !exact ? `<div class="nv" data-nv="1">＋ Créer le chantier « ${esc(inp.value.trim())} »</div>` : "");
  };
  inp.addEventListener("input", () => { if (choisi !== "nouveau") choisi = null; maj(); });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { const premier = liste.querySelector("div"); if (premier) { e.preventDefault(); premier.click(); } }
  });
  maj();
  liste.addEventListener("click", (e) => {
    const x = e.target.closest("div");
    if (!x) return;
    if (x.dataset.nv) {
      const m = inp.value.trim().match(/^(\d[\d ]*\d|\d+)?\s*-?\s*(.*)$/);
      nv.hidden = false;
      nv.querySelector("[name=numero]").value = (m[1] || "").trim();
      nv.querySelector("[name=nom]").value = m[2] || "";
      nv.querySelector(m[2] ? "[name=resp]" : "[name=nom]").focus();
      choisi = "nouveau";
      surChoix?.(choisi);
      return;
    }
    choisi = Number(x.dataset.c);
    nv.hidden = true;
    inp.value = libelleCh(chantier(choisi));
    maj();
    surChoix?.(choisi);
  });
  return async () => {
    if (choisi === "nouveau") {
      const c = await api("POST", "/api/chantiers", {
        numero: nv.querySelector("[name=numero]").value, nom: nv.querySelector("[name=nom]").value,
        responsable: nv.querySelector("[name=resp]").value, facturable: nv.querySelector("[name=fact]").checked,
      });
      D.chantiers.push(c);
      choisi = c.id;
      notifier(`Chantier « ${libelleCh(c)} » créé.`);
      return c.id;
    }
    if (!choisi) throw new Error("Choisissez un chantier dans la liste (ou créez-en un).");
    return choisi;
  };
}

function fenetreCreation(artId, debut, fin, alFermer) {
  const options = visibles().map((a) => `<option value="${a.id}" ${a.id === artId ? "selected" : ""}>${esc(a.categorie_nom)} — ${esc(a.numero_interne)}</option>`).join("");
  const dlg = fenetre(`
    <h2>Nouvelle affectation</h2>
    <p class="sous">Pas d'affectation = matériel disponible au dépôt.</p>
    <label class="champ"><span>Article</span><select class="art">${options}</select></label>
    <div class="deux">
      <label class="champ"><span>Du</span><input class="d1" value="${jj(debut)}" placeholder="JJ.MM.AAAA"></label>
      <label class="champ"><span>Au (inclus)</span><input class="d2" value="${jj(fin)}" placeholder="JJ.MM.AAAA"></label>
    </div>
    ${BLOC_CHANTIER}
    <label class="champ"><span>Responsable pour cette affectation (si différent de celui du chantier)</span><input class="resp" placeholder="Laisser vide = responsable du chantier"></label>
    <label class="champ"><span>Remarque</span><input class="rem"></label>
    <div class="actions"><button data-annuler>Annuler</button><button class="primaire" data-ok>Enregistrer</button></div>`);
  const valider = selecteurChantier(dlg);
  dlg.addEventListener("close", () => alFermer?.());
  dlg.querySelector("[data-annuler]").onclick = () => dlg.close();
  dlg.querySelector(artId ? ".rch" : ".art").focus();
  dlg.querySelector("[data-ok]").onclick = async () => {
    try {
      const d1 = lireDate(dlg.querySelector(".d1").value), d2 = lireDate(dlg.querySelector(".d2").value);
      if (!d1 || !d2) throw new Error("Dates invalides (format JJ.MM.AAAA).");
      const corps = {
        article_id: Number(dlg.querySelector(".art").value), chantier_id: await valider(),
        date_debut: d1, date_fin: d2, responsable: dlg.querySelector(".resp").value, remarque: dlg.querySelector(".rem").value,
      };
      dlg.close();
      await enregistrer("POST", "/api/affectations", corps);
    } catch (e) { erreur(e); }
  };
}

function fenetreModification(af) {
  const a = article(af.article_id);
  const auj = aujourdhuiIso();
  const ref = auj >= af.date_debut && auj < af.date_fin ? auj : af.date_fin;
  const lendemain = plus(ref, 1) <= af.date_fin ? plus(ref, 1) : af.date_fin;
  const dlg = fenetre(`
    <h2><span class="echantillon" style="background:${esc(a.couleur)}"></span> ${esc(a.numero_interne)} — ${esc(libelle(af))}</h2>
    <p class="sous">Du ${jj(af.date_debut)} au ${jj(af.date_fin)} · ${duree(af.date_debut, af.date_fin)} jour(s)</p>
    <div class="rapide"><h3>Actions rapides</h3>
      <div class="l"><button data-q="rendre">Rendre au dépôt</button> dernier jour sur le chantier : <input class="dr" value="${jj(ref)}"></div>
      <div class="l"><button data-q="changer">Changer de chantier</button> à partir du : <input class="dc" value="${jj(lendemain)}"></div>
      <div class="l"><button data-q="couper">Couper en deux</button> à partir du : <input class="dx" value="${jj(lendemain)}"></div>
      <p class="doux" style="margin:4px 0 0">Pour « Changer de chantier », choisissez d'abord le nouveau chantier ci-dessous.</p>
    </div>
    ${BLOC_CHANTIER}
    <div class="deux">
      <label class="champ"><span>Du</span><input class="d1" value="${jj(af.date_debut)}"></label>
      <label class="champ"><span>Au (inclus)</span><input class="d2" value="${jj(af.date_fin)}"></label>
    </div>
    <label class="champ"><span>Responsable pour cette affectation</span><input class="resp" value="${esc(af.responsable)}" placeholder="${esc(af.chantier_responsable || "Responsable du chantier")}"></label>
    <label class="champ"><span>Remarque</span><input class="rem" value="${esc(af.remarque)}"></label>
    <div class="actions">
      <button class="danger" data-sup style="margin-right:auto">Supprimer</button>
      <button data-annuler>Fermer</button><button class="primaire" data-ok>Enregistrer</button>
    </div>`);
  let autreChantier = false;
  const valider = selecteurChantier(dlg, af.chantier_id, (c) => { autreChantier = c !== af.chantier_id; });
  const date = (sel, nom) => { const d = lireDate(dlg.querySelector(sel).value); if (!d) throw new Error(`Date « ${nom} » invalide.`); return d; };
  const action = async (fn) => { try { await fn(); dlg.close(); await rafraichir(); } catch (e) { erreur(e); } };

  dlg.querySelector("[data-annuler]").onclick = () => dlg.close();
  dlg.querySelector('[data-q="rendre"]').onclick = () => action(async () => {
    await api("POST", `/api/affectations/${af.id}/rendre`, { date: date(".dr", "Dernier jour") });
    notifier(`${a.numero_interne} rendu au dépôt.`);
  });
  dlg.querySelector('[data-q="changer"]').onclick = () => {
    if (!autreChantier) { erreur(new Error("Choisissez d'abord le nouveau chantier dans la liste.")); dlg.querySelector(".rch").select(); return; }
    action(async () => {
      const d = date(".dc", "À partir du");
      const ch = await valider();
      await api("POST", `/api/affectations/${af.id}/couper`, { date: d, chantier_id: ch, responsable: dlg.querySelector(".resp").value === af.responsable ? "" : dlg.querySelector(".resp").value });
      notifier(`${a.numero_interne} change de chantier le ${jj(d)}.`);
    });
  };
  dlg.querySelector('[data-q="couper"]').onclick = () => action(async () => {
    await api("POST", `/api/affectations/${af.id}/couper`, { date: date(".dx", "À partir du") });
  });
  dlg.querySelector("[data-sup]").onclick = async () => {
    if (!(await confirmer(`Supprimer l'affectation de ${a.numero_interne} sur « ${libelle(af)} » ?`, { ok: "Supprimer", danger: true }))) return;
    action(() => api("DELETE", `/api/affectations/${af.id}`));
  };
  dlg.querySelector("[data-ok]").onclick = async () => {
    try {
      const corps = {
        ...corpsDe(af), chantier_id: await valider(), date_debut: date(".d1", "Du"), date_fin: date(".d2", "Au"),
        responsable: dlg.querySelector(".resp").value, remarque: dlg.querySelector(".rem").value,
      };
      dlg.close();
      await enregistrer("PUT", `/api/affectations/${af.id}`, corps);
    } catch (e) { erreur(e); }
  };
}
