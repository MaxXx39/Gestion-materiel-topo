# Planning du matériel topo

Application pour gérer le parc de matériel topographique (cannes GPS, stations totales, Hilti PLT, caméras…), le planning des affectations aux chantiers et l'export mensuel pour la comptabilité.

Tout fonctionne **sur votre PC, sans Internet** (sauf au premier lancement, pour l'installation). Aucune donnée ne part dans le cloud.

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

Astuce : clic droit sur `Lancer.bat` → **Envoyer vers** → **Bureau (créer un raccourci)**.

Si vous avez fermé l'onglet du navigateur sans fermer la fenêtre noire, double-cliquez à nouveau sur `Lancer.bat` : l'application se rouvre.

## 4. Premier démarrage : reprendre votre Excel

Menu **Parc** → **« Importer depuis l'Excel »**, puis choisissez votre fichier actuel (`GESTION_GPS_V2.xlsx`).

L'application lit les catégories, les articles (codes compta, couleurs), les chantiers (n° et nom, sans le responsable) et les affectations (barres du planning).

1. Vérifiez les chantiers marqués **« À vérifier »** et corrigez leur nom directement dans le tableau.
2. Cliquez sur **« Importer la sélection »**.
3. Si certaines affectations n'ont pas pu être importées, elles sont listées pour que vous les ajoutiez vous-même.

Le fichier est lu sur votre PC uniquement. Relancer l'import ne crée pas de doublons.

## 5. Utiliser le planning

- **Créer une affectation :** glissez la souris sur les jours de la ligne d'un article, puis choisissez le chantier (tapez un n° ou un nom, puis Entrée). S'il n'existe pas, cliquez sur « ＋ Créer le chantier… ».
- **Allonger / raccourcir :** tirez le bord gauche ou droit d'une barre.
- **Déplacer :** faites glisser une barre.
- **Modifier :** cliquez sur une barre. Actions rapides : « Rendre au dépôt », « Changer de chantier à partir du… », « Couper en deux ».
- **Chevauchement :** l'application demande s'il faut couper l'affectation existante, la remplacer ou annuler.
- **Annuler une erreur :** bouton « ↶ Annuler » ou Ctrl+Z (jusqu'à 30 retours, tant que l'application reste ouverte).
- **Repérer :** tapez un chantier ou un article dans le champ « Repérer » pour faire ressortir ses barres.
- **Vue année :** bouton « Année » ; cliquez sur un mois pour l'ouvrir.
- Dates au clavier : « 5.10 », « 5.10.26 » ou « 05.10.2026 » sont acceptés.

## 6. Export du mois pour la compta

Sur le planning, affichez le mois voulu puis cliquez sur **« Exporter le mois »** :

- **`AAAA_MM.pdf`** (ex. `2026_10.pdf`) : la page A4 paysage pour la compta ;
- **`AAAA_MM.xlsx`** : la même mise en page dans Excel, modifiable par quelqu'un d'autre en votre absence (il n'est pas réimporté).

Les fichiers arrivent dans votre dossier **Téléchargements**. Si le navigateur demande l'autorisation de télécharger plusieurs fichiers, acceptez.

## 7. Parc, fiches et tableau de bord

- **Parc :** recherche, filtres, tri, colonne « Où est-il aujourd'hui ? », bouton « ⬇ Excel » (inventaire).
- **Fiche article :** photo, documents (notice, certificat, facture…), historique des affectations, accessoires (champ « Accessoire de » ou bouton « ＋ Ajouter un accessoire »). « Dupliquer » reprend la fiche pour un matériel identique.
- **Statut :** un article « En réparation », « Perdu » ou « Réformé » disparaît du planning (case « Inactifs » pour le revoir), son historique est conservé.
- **Tableau de bord :** nombre d'articles, affectés, disponibles, en réparation, valeur du parc, fins d'affectation dans les 7 jours.

## 8. Sauvegarder et restaurer

Menu **Sauvegarde** :

- **Sauvegarder :** « Télécharger une sauvegarde » crée un fichier `.zip` avec **toutes** les données (photos et documents compris). Rangez-le sur une clé USB ou un disque réseau. Conseil : une fois par mois, après l'envoi à la compta.
- **Restaurer :** glissez un fichier de sauvegarde `.zip` dans la zone « Restaurer ». Une copie de sécurité des données actuelles est faite automatiquement avant (`donnees\sauvegardes_auto`).
- **Exports Excel :** inventaire du parc et liste complète des affectations.

## 9. Où sont mes données ?

Dans le dossier **`donnees`**, à côté de `Lancer.bat` :

- `donnees\planning.db` : articles, chantiers, affectations ;
- `donnees\fichiers\` : photos et documents joints ;
- `donnees\sauvegardes_auto\` : copies de sécurité faites avant chaque restauration.

## 10. Mettre à jour l'application

1. Faites une sauvegarde (menu Sauvegarde), puis fermez la fenêtre noire.
2. Téléchargez et extrayez la nouvelle version.
3. Copiez votre dossier `donnees` dans le nouveau dossier.
4. Relancez `Lancer.bat`.

Vos données sont conservées : l'application met à jour leur format automatiquement si nécessaire.

---

## Pour aller plus loin (facultatif)

- Lancement sans `Lancer.bat` : `python app/serveur.py` (après `pip install -r requirements.txt`).
- Tests automatiques : `python -m unittest discover tests`.
- Organisation du code :
  - `app/serveur.py` démarre l'application (port libre entre 47310 et 47329) ;
  - `app/api.py` : le serveur (enregistrement des données) ;
  - `app/base.py` : la base de données ;
  - `app/import_excel.py` : lecture de l'ancien Excel ;
  - `app/export_mois.py` : PDF et Excel mensuels ;
  - `app/sauvegarde.py` : sauvegarde / restauration ;
  - `app/static/` : l'interface (HTML, CSS, JavaScript) ;
  - `app/polices/` : police Carlito (même gabarit que Calibri) pour le PDF.
- `maquette/maquette.html` : maquette validée, utilisée comme référence.
