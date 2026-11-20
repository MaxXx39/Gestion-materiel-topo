// Point d'entrée de l'interface : choisit la page à afficher selon l'adresse (#/parc, #/article/12…).
import { erreur } from "./outils.js";
import pageParc from "./pages/parc.js";
import pageArticle from "./pages/article.js";
import pageChantiers from "./pages/chantiers.js";
import pageCategories from "./pages/categories.js";
import pagePreremplir from "./pages/preremplir.js";
import pagePlanning from "./pages/planning.js";
import { pageAVenir } from "./pages/a-venir.js";

const PAGES = {
  planning: pagePlanning,
  parc: pageParc,
  article: pageArticle,
  chantiers: pageChantiers,
  categories: pageCategories,
  preremplir: pagePreremplir,
  tableau: pageAVenir("Tableau de bord", "Le tableau de bord arrive à l'étape 5."),
};

async function afficher() {
  const adresse = location.hash.replace(/^#\/?/, "");
  const [chemin, requete = ""] = adresse.split("?");
  const [nom, ...args] = chemin.split("/");
  const page = PAGES[nom] ? nom : "planning";
  document.querySelectorAll("#menu a").forEach((a) => {
    const actif = a.dataset.page === page || ((page === "article" || page === "preremplir") && a.dataset.page === "parc");
    a.classList.toggle("actif", actif);
  });
  const zone = document.getElementById("page");
  zone.innerHTML = "";
  window.scrollTo(0, 0);
  try {
    await PAGES[page](zone, args, new URLSearchParams(requete));
  } catch (e) {
    erreur(e);
  }
}

window.addEventListener("hashchange", afficher);
afficher();
