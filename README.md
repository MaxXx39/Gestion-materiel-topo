# Planning du matériel topo

Application pour gérer le parc de matériel topographique (cannes GPS, stations totales, Hilti PLT, caméras…), le planning des affectations aux chantiers et le PDF mensuel pour la comptabilité.

Tout fonctionne **sur votre PC, sans Internet** (sauf au premier lancement, pour l'installation). Aucune donnée ne part dans le cloud.

> **État actuel : étape 1** — catégories, articles (avec photo et documents) et chantiers.
> Pré-remplissage des articles et chantiers depuis votre Excel : disponible.
> À venir : planning visuel (étape 2), import de l'Excel (étape 3), PDF + Excel mensuels (étape 4), tableau de bord et sauvegarde en un clic (étape 5).

---

## 1. Installer Python (une seule fois)

1. Allez sur <https://www.python.org/downloads/> et cliquez sur le gros bouton jaune **Download Python**.
2. Lancez le fichier téléchargé.
3. **Important :** en bas de la première fenêtre, cochez **« Add python.exe to PATH »**.
4. Cliquez sur **Install Now** et attendez la fin.

## 2. Récupérer l'application

1. Téléchargez le fichier ZIP de l'application.
2. Faites un clic droit sur le fichier ZIP → **Extraire tout…**
3. Placez le dossier obtenu où vous voulez, par exemple dans `Documents\Planning materiel`.

## 3. Lancer l'application

Double-cliquez sur **`Lancer.bat`**.

- Le **premier lancement** prend 1 à 2 minutes (installation des composants, connexion Internet nécessaire).
- Ensuite, le navigateur s'ouvre tout seul sur l'application.
- **Laissez la fenêtre noire ouverte** pendant que vous travaillez. Pour arrêter l'application, fermez cette fenêtre.

> Si Windows affiche « Windows a protégé votre ordinateur », cliquez sur **Informations complémentaires** puis **Exécuter quand même**.

Astuce : faites un clic droit sur `Lancer.bat` → **Envoyer vers** → **Bureau (créer un raccourci)** pour lancer l'application depuis le bureau.

Si vous avez fermé l'onglet du navigateur sans fermer la fenêtre noire, double-cliquez à nouveau sur `Lancer.bat` : l'application se rouvre.

## 4. Premier démarrage : reprendre votre Excel

Dans **Parc**, cliquez sur **« Pré-remplir depuis l'Excel »** et choisissez votre fichier actuel (`GESTION_GPS_V2.xlsx`).
L'application crée les catégories, les articles (codes compta, couleurs) et les chantiers (n° et nom, sans le responsable).
Avant de valider, vérifiez les chantiers marqués **« À vérifier »** : corrigez leur nom directement dans le tableau.
Le fichier est lu sur votre PC uniquement. Vous pouvez relancer l'opération : ce qui existe déjà n'est pas dupliqué.

## 5. Où sont mes données ?

Toutes vos données sont dans le dossier **`donnees`**, à côté de `Lancer.bat` :

- `donnees\planning.db` : articles, chantiers, affectations ;
- `donnees\fichiers\` : photos et documents joints.

## 6. Sauvegarder et restaurer

Un bouton « Sauvegarde » arrivera à l'étape 5. En attendant :

- **Sauvegarder :** fermez la fenêtre noire, puis copiez le dossier `donnees` sur une clé USB ou un disque réseau.
- **Restaurer :** fermez la fenêtre noire, puis remplacez le dossier `donnees` par votre copie.

## 7. Mettre à jour l'application

1. Fermez la fenêtre noire.
2. Téléchargez et extrayez la nouvelle version.
3. Copiez votre dossier `donnees` dans le nouveau dossier (ou copiez les nouveaux fichiers par-dessus l'ancien dossier **sans toucher à `donnees`**).
4. Relancez `Lancer.bat`.

Vos données sont conservées : l'application met à jour leur format automatiquement si nécessaire.

---

## Pour aller plus loin (facultatif)

- Lancement sans `Lancer.bat` : `python app/serveur.py` (après `pip install -r requirements.txt`).
- Tests automatiques : `python -m unittest discover tests`.
- Organisation du code :
  - `app/serveur.py` démarre l'application ;
  - `app/api.py` contient le serveur (enregistrement des données) ;
  - `app/base.py` décrit la base de données ;
  - `app/static/` contient l'interface (HTML, CSS, JavaScript).
- `maquette/maquette.html` : maquette validée, utilisée comme référence.
