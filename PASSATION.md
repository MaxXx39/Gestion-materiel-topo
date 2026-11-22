# Passation – Planning du matériel topo

Document destiné à une autre session (humaine ou Claude Code) qui doit reprendre cette fonction, par exemple pour l'intégrer dans l'application **app-topo**. Il résume ce qui ne se lit pas directement dans le code : le contexte, les choix de l'utilisateur et les points fragiles.

État au 22.11.2026 – branche `claude/eager-davinci-yksmd0` du dépôt `MaxXx39/Gestion-materiel-topo`.

---

## 1. À quoi sert l'appli

- **Qui :** un géomètre d'une entreprise de gros œuvre (génie civil et bâtiment), **seul utilisateur**, sur **son PC Windows**. Débutant en développement : l'installation et la maintenance doivent rester très simples.
- **Pour quoi :** gérer un parc d'environ 25 appareils de mesure (cannes GPS, stations totales robotisées / théodolites, Hilti PLT400, caméras, détecteur, guidage 3D machine) et **savoir sur quel chantier se trouve chaque appareil, jour par jour**.
- **Le besoin principal :** chaque mois, envoyer à la comptabilité un **PDF du planning du mois** pour qu'elle facture le matériel au bon chantier (une colonne « N° MS – à facturer » = code article compta).
- **Ce qu'elle remplace :** un fichier Excel avec une colonne par jour de l'année et des cellules fusionnées en couleur (long à remplir, mise en page fragile, à dupliquer chaque mois).
- Il n'y a **pas** de notion de « sortie / retour » par une personne : on affecte un appareil **à un chantier** pour une période. Pas d'affectation un jour donné = l'appareil est **disponible au dépôt**.

## 2. Écrans et fonctions

Menu latéral à gauche (style « Chantier » : menu sombre, accent orange).

1. **Planning** (écran d'accueil)
   - Vue **mois** : articles en lignes, regroupés par catégorie (nom de catégorie à la verticale), un jour par colonne (n° du jour + jour abrégé « lun, mar… »). Week-ends grisés, jour actuel surligné.
   - La **première colonne (hachurée)** montre le **dernier jour du mois précédent** : on tire le bord droit d'une barre qui s'y termine pour la prolonger dans le mois.
   - **Glisser** sur les jours d'une ligne → nouvelle affectation (choix du chantier par recherche, ou création du chantier à la volée).
   - **Tirer le bord** d'une barre → allonger / raccourcir. **Glisser** une barre → la déplacer. Une bulle affiche les dates pendant le geste.
   - **Clic** sur une barre → fenêtre de modification : dates, chantier, responsable, remarque, et actions rapides **« Rendre au dépôt »**, **« Changer de chantier à partir du… »**, **« Couper en deux »**, **« Supprimer »**.
   - **Chevauchement** interdit : l'appli demande **couper l'existante / remplacer / annuler**.
   - **« ↦ Prolonger <mois précédent> »** : liste les affectations finissant le dernier jour du mois précédent (cochées) et les prolonge d'un coup.
   - **↶ Annuler** (Ctrl+Z, 30 niveaux), champ **« Repérer »** (fait ressortir un chantier ou un article), **« ＋ Saisie »** (formulaire clavier), case **« Inactifs »**, vue **Année** (lecture seule, clic sur un mois pour l'ouvrir).
   - **« Exporter le mois »** → `AAAA_MM.pdf` (pour la compta) et `AAAA_MM.xlsx` (même planning, modifiable par un collègue).
2. **Parc** : liste des articles avec recherche, filtres (catégorie, statut, disponible / affecté aujourd'hui), tri par colonne, colonne **« Où est-il aujourd'hui ? »**, bouton « ⬇ Excel » (inventaire), bouton **« Importer depuis l'Excel »**.
3. **Fiche article** : catégorie, n° interne, désignation, code compta, couleur (palette de 20 + couleur libre), statut, marque, modèle, n° de série, date d'achat, prix CHF, fournisseur, fin de garantie, **n° de téléphone (carte SIM)**, **n° et mot de passe Swipos**, notes, **photo**, **documents joints**, **historique des affectations**, **accessoires**. Boutons « Enregistrer et ajouter un autre », « Dupliquer ».
4. **Chantiers** : liste + fenêtre d'édition (n°, nom, responsable, facturable, archivé, notes). Les responsables déjà saisis sont proposés à la frappe.
5. **Catégories** : ordre des catégories et des articles (▲ ▼) = ordre du planning et du PDF ; renommer ; bouton **« 🎨 Recolorer tout le parc »**.
6. **Tableau de bord** : nombre d'articles, affectés aujourd'hui, disponibles, en réparation, valeur du parc (CHF), liste des disponibles, fins d'affectation dans les 7 jours.
7. **Sauvegarde** : télécharger une sauvegarde `.zip` complète, restaurer (glisser un `.zip`), exports Excel (inventaire, liste des affectations).
8. **Importer depuis l'Excel** (depuis Parc) : lit l'ancien `GESTION_GPS_V2.xlsx` et propose, avant tout enregistrement, articles, chantiers et affectations à vérifier / corriger.

## 3. Les données

### Forme et emplacement
- **Base SQLite** : un seul fichier `donnees/planning.db`, à côté de `Lancer.bat`.
- **Fichiers joints** : `donnees/fichiers/photos/` et `donnees/fichiers/documents/` (noms de fichiers aléatoires, nom d'origine gardé en base).
- **Copies de sécurité** automatiques avant restauration : `donnees/sauvegardes_auto/`.
- Rien dans le navigateur (pas d'IndexedDB ni de localStorage), rien dans le cloud. Le dossier `donnees/` est exclu de Git (`.gitignore`).
- L'emplacement peut être changé avec la variable d'environnement `PLANNING_DONNEES` (utilisé par les tests).
- Dates stockées en **ISO** (`2026-10-31`), affichées en **JJ.MM.AAAA**. Montants en CHF (nombre décimal).

### Tables (voir `app/base.py`)
- `categorie` (id, nom unique, ordre)
- `article` (id, categorie_id, ordre, **numero_interne unique**, designation, **code_compta non unique**, couleur `#RRGGBB`, marque, modele, numero_serie, date_achat, prix_chf, fournisseur, fin_garantie, notes, **statut** ∈ actif / reparation / perdu / reforme, photo, parent_id (accessoire de), telephone, swipos_numero, swipos_mot_de_passe, cree_le, modifie_le)
- `document` (id, article_id, nom_original, fichier, ajoute_le)
- `chantier` (id, numero, cle_numero = chiffres seuls pour l'unicité, nom, responsable, facturable, archive, notes)
- `affectation` (id, article_id, chantier_id, date_debut, date_fin – **incluses** –, responsable = remplace celui du chantier si rempli, remarque)
- Schéma versionné par `PRAGMA user_version` : liste `MIGRATIONS` dans `base.py` (on ajoute à la fin, on ne modifie jamais une ancienne entrée).

### Exemple réel (réponse de l'API, responsable fictif)
```json
{
  "article": { "id": 1, "categorie_nom": "Canne GPS", "numero_interne": "953", "code_compta": "112",
               "couleur": "#F4A6B8", "statut": "actif", "telephone": "", "swipos_numero": "" },
  "chantier": { "id": 5, "numero": "10 203", "cle_numero": "10203", "nom": "OFROU PAB",
                "responsable": "M. Dupont", "facturable": 1, "archive": 0 },
  "affectation": { "id": 12, "article_id": 1, "chantier_id": 5,
                   "date_debut": "2026-10-19", "date_fin": "2026-11-13", "responsable": "", "remarque": "" }
}
```
Texte affiché sur la barre : `10 203 – OFROU PAB – M. Dupont` (le responsable en plus petit, en italique).

## 4. La technique

- **Langage :** Python 3 côté serveur, HTML / CSS / JavaScript « vanilla » (modules ES) côté interface. **Aucune étape de construction** (pas de npm, pas de bundler).
- **Bibliothèques** (`requirements.txt`, versions figées) :
  - `flask` : petit serveur web local et API JSON ;
  - `waitress` : serveur de production simple sous Windows (évite l'avertissement rouge du serveur de développement Flask) ;
  - `openpyxl` : lecture de l'ancien Excel, exports Excel (mensuel, inventaire, affectations) ;
  - `reportlab` : PDF mensuel dessiné au point près.
  - Police **Carlito** (licence libre OFL, même gabarit que Calibri) embarquée dans `app/polices/` pour le PDF.
- **Fonctionnement :** `app/serveur.py` démarre Waitress sur `127.0.0.1` (accessible seulement depuis le PC), sur le premier port libre entre **47310 et 47329**, et ouvre le navigateur. Il vérifie `/api/identite` pour ne pas se confondre avec une autre appli déjà lancée sur le même port.

### Dossiers et fichiers importants
```
Lancer.bat              Lanceur Windows : crée .venv au 1er lancement, installe requirements, lance app/serveur.py
requirements.txt
README.md               Mode d'emploi pour l'utilisateur (installer, lancer, sauvegarder…)
app/serveur.py          Démarrage, choix du port, ouverture du navigateur
app/api.py              Toutes les routes /api/… (catégories, articles, chantiers, affectations,
                        import, exports, sauvegarde) + règles métier (chevauchements, couper, prolonger, annuler)
app/base.py             Emplacement des données, schéma SQLite et migrations, normalisation des n° de chantier
app/import_excel.py     Lecture de l'ancien planning Excel (cellules fusionnées, couleurs du thème, recollage des mois)
app/export_mois.py      PDF mensuel (reportlab) et Excel mensuel (openpyxl)
app/sauvegarde.py       Création / restauration du .zip (base + fichiers)
app/polices/            Carlito Regular / Bold / Italic (+ licence)
app/static/index.html   Coquille de l'interface (menu)
app/static/style.css    Tout le style (style « Chantier »)
app/static/js/app.js    Routeur (#/planning, #/parc, #/article/12…)
app/static/js/outils.js Appels API, dates JJ.MM.AAAA, CHF, palette de 20 couleurs, fenêtres
app/static/js/pages/    Un fichier par écran : planning, parc, article, chantiers, categories,
                        tableau, sauvegarde, preremplir (= import Excel)
tests/test_api.py       Tests automatiques du serveur (21 tests, unittest)
maquette/               Maquette HTML validée + captures des 3 styles proposés (référence visuelle)
```

### Lancer et tester
- Utilisateur Windows : double-clic sur `Lancer.bat`.
- Développeur :
  ```bash
  pip install -r requirements.txt
  python app/serveur.py                      # ouvre le navigateur
  python app/serveur.py --sans-navigateur    # sans ouvrir le navigateur
  PLANNING_DONNEES=/tmp/essai python app/serveur.py   # base de test séparée
  python -m unittest discover tests          # tests du serveur
  ```
- Les tests de bout en bout (navigateur piloté par Playwright) ont été faits **à la main pendant le développement** ; leurs scripts ne sont **pas** dans le dépôt.

## 5. Décisions prises en conversation (invisibles dans le code)

- **100 % local**, pas de cloud, pas de compte, un seul utilisateur. Données dans un fichier facile à sauvegarder (pas dans le stockage du navigateur).
- Stack choisie pour un débutant : Python + Flask + SQLite + JS sans framework ; validée par l'utilisateur. Une version « un seul fichier HTML sans Python » a été évoquée et **écartée** (permissions fichiers, PDF moins précis).
- **Style visuel C « Chantier »** choisi parmi trois propositions (A classique, B épuré, C chantier).
- **Code compta (N° MS)** : jamais une clé (il se répète : 111, 104…). Le **n° interne** est unique.
- **Responsable** : par défaut celui du chantier, **remplaçable par affectation**. Lors de l'import Excel, les responsables **ne sont pas repris** (choix explicite : « sans l'utilisateur »). Dans les barres, il est affiché plus discrètement.
- Chantiers internes (ex. « RONCHI », « GEOMETRE - MGO ») : **gérés comme les autres** (facturables par défaut, présents sur le PDF).
- Lignes vides « Guidage 3D » de l'Excel : importées comme articles provisoires « Guidage 3D Machine 1 / 2 / 3 ».
- Cellule isolée « 10195 » de l'Excel = chantier « 10 195 » (un seul jour).
- N° de chantier écrits différemment mais avec les mêmes chiffres = **un seul chantier** (`cle_numero`). « 855325 » est normalisé en « 855 325 ».
- **Chevauchements interdits** ; l'utilisateur choisit couper / remplacer / annuler.
- **« Prolonger »** : une affectation prolongée s'arrête la veille de l'affectation suivante de l'article.
- **PDF mensuel** : au départ copie fidèle du modèle Excel, puis l'utilisateur a autorisé des améliorations tant que **les mêmes informations** y sont (pleine largeur, jours à l'horizontale, week-ends grisés, nombre de jours par barre, triangles de continuité, pied de page). Une page A4 paysage, nom `AAAA_MM.pdf`. Un article non actif apparaît sur le PDF s'il a été affecté dans le mois (pour être facturé).
- **Excel mensuel** : garde la disposition de l'ancien fichier, pour qu'un collègue le modifie en l'absence de l'utilisateur. **Il n'est pas réimporté** (choix explicite).
- **Week-ends grisés** : refusés au départ, puis demandés par l'utilisateur (écran et PDF).
- **Mot de passe Swipos** : stocké en clair dans la base locale ; **jamais** dans les exports Excel.
- Les données réelles (Excel, chantiers, responsables) **ne doivent pas être commitées** : le dépôt est public. L'import lit le fichier Excel sur le PC.
- **Hors périmètre** (demandé par l'utilisateur) : multi-utilisateurs et droits, alertes de retard, suivi d'étalonnage / maintenance planifiée, récapitulatif de facturation par chantier, QR codes, version mobile.

## 6. État : ce qui marche, ce qui n'a pas été essayé, ce qui reste

**Testé et fonctionnel (sous Linux, navigateur Chromium piloté) :**
- import complet de l'Excel réel : 5 catégories, 24 articles, 40 chantiers, 62 affectations, aucune refusée ;
- PDF d'octobre comparé visuellement au PDF d'origine : mêmes barres, dates, couleurs ;
- créer / étirer / déplacer / couper / rendre / changer de chantier / prolonger / annuler ;
- sauvegarde puis restauration (photos comprises) ; exports Excel ; mise à jour d'une ancienne base (migration) ;
- 21 tests automatiques au vert.

**Jamais essayé sur le terrain :**
- **`Lancer.bat` sous Windows** (écrit pour Windows, jamais exécuté dans ce contexte). Seul retour de l'utilisateur : la première version prenait le même port qu'une autre de ses applis, corrigé depuis (ports 47310–47329 + identification).
- Impression réelle du PDF et de l'Excel mensuels ; ouverture de l'Excel dans Microsoft Excel (vérifié seulement avec LibreOffice) ; envoi à la compta.
- Usage quotidien sur plusieurs mois, gros volumes de photos / documents, restauration d'une grosse sauvegarde.

**Reste à faire / pistes :**
- Faire valider le tout par l'utilisateur sur son PC.
- Retirer la maquette du dépôt public (voir pièges).
- Éventuellement : appliquer au PDF-Excel les mêmes améliorations que le PDF ; jours fériés ; densité des lignes ; tests de bout en bout versionnés.

## 7. Pièges connus

- **Dépôt public** : `maquette/maquette.html` contient des **noms réels de chantiers et de responsables** (données de l'Excel embarquées). À retirer (historique compris) ou rendre le dépôt privé.
- **Annulation (Ctrl+Z)** : pile **en mémoire** du serveur → perdue au redémarrage ; ne concerne **que les affectations** (pas les articles ni les chantiers). Elle restaure toute la table des affectations ; si un article ou un chantier a été supprimé entre-temps, l'annulation est refusée.
- **Import Excel** dépendant de la structure de l'ancien fichier : une seule feuille, date du 1er jour en **D2**, articles à partir de la ligne 4, catégorie en colonne A (fusion verticale), code en B, n° interne en C (sa couleur = couleur de l'article), barres = **cellules fusionnées**. Le découpage « n° – nom – responsable » est une heuristique : les cas douteux sont marqués « À vérifier » ; d'autres peuvent être faux sans être signalés (ex. un lieu pris pour un responsable).
- **Dates côté JS** : calculées en UTC à partir de chaînes ISO, pour éviter les décalages d'heure d'été. Ne pas mélanger avec des `Date` locales.
- La date « aujourd'hui » est celle du PC.
- **Restauration** : remplace le fichier `planning.db` et tout le dossier `fichiers/`. Sous Windows, un fichier ouvert ailleurs (ex. une photo ouverte dans une visionneuse) pourrait bloquer l'opération.
- **« Télécharger les deux »** (PDF + Excel) déclenche deux téléchargements : certains navigateurs demandent une autorisation ou en bloquent un ; les deux boutons séparés restent disponibles.
- **Recolorer tout le parc** écrase toutes les couleurs personnalisées.
- **Accessoires** : un seul niveau (un accessoire ne peut pas avoir d'accessoire) ; ils apparaissent comme des articles normaux dans le planning et le PDF.
- Pas d'authentification : sécurité assurée uniquement par l'écoute sur `127.0.0.1`.
- `Lancer.bat` doit garder des fins de ligne **CRLF** (`.gitattributes` : `*.bat -text`). Les messages du `.bat` sont sans accents volontairement (encodage de la console Windows).
- Le premier lancement nécessite Internet (installation des paquets) ; ensuite tout fonctionne hors ligne. Les paquets ne sont réinstallés que si `requirements.txt` change.

## 8. Fichiers à reprendre en priorité pour copier la fonction ailleurs

1. **`app/base.py`** – le modèle de données (schéma + migrations) : à transposer dans le stockage de l'appli cible.
2. **`app/api.py`**, partie « Affectations » (`chevauchements`, `resoudre_chevauchements`, `poser`, routes `couper`, `rendre`, `prolonger`, `annuler`) – **les règles métier du planning**.
3. **`app/static/js/pages/planning.js`** – l'écran principal (grille du mois, colonne du mois précédent, glisser / étirer / déplacer, fenêtres) et **la partie planning de `app/static/style.css`**.
4. **`app/export_mois.py`** – PDF et Excel mensuels pour la compta (+ `app/polices/`).
5. **`app/static/js/outils.js`** – dates JJ.MM.AAAA, saisie rapide de dates, CHF, palette de 20 couleurs.
6. **`app/import_excel.py`** – seulement si l'ancien Excel doit encore être repris.
7. Ensuite, selon les besoins : `pages/article.js` (fiche), `pages/parc.js`, `pages/chantiers.js`, `app/sauvegarde.py`, `pages/tableau.js`.
8. Pour la référence visuelle : `maquette/maquette.html` (validée par l'utilisateur), **à ne pas recopier telle quelle dans un dépôt public** (données réelles).
