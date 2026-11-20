"""Base de données SQLite : emplacement des fichiers, création et mises à jour du schéma."""
import os
import re
import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = Path(os.environ.get("PLANNING_DONNEES", RACINE / "donnees"))
FICHIER_BASE = DOSSIER_DONNEES / "planning.db"
DOSSIER_FICHIERS = DOSSIER_DONNEES / "fichiers"

STATUTS = {
    "actif": "Actif",
    "reparation": "En réparation / SAV",
    "perdu": "Perdu / volé",
    "reforme": "Réformé / vendu",
}

# Chaque élément de la liste est une mise à jour du schéma. On n'en modifie
# jamais une ancienne : on en ajoute une nouvelle à la fin. Ainsi, vos données
# existantes sont conservées quand l'application évolue.
MIGRATIONS = [
    """
    CREATE TABLE categorie (
        id     INTEGER PRIMARY KEY,
        nom    TEXT NOT NULL UNIQUE COLLATE NOCASE,
        ordre  INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE article (
        id              INTEGER PRIMARY KEY,
        categorie_id    INTEGER NOT NULL REFERENCES categorie(id),
        ordre           INTEGER NOT NULL DEFAULT 0,
        numero_interne  TEXT NOT NULL UNIQUE COLLATE NOCASE,
        designation     TEXT NOT NULL DEFAULT '',
        code_compta     TEXT NOT NULL DEFAULT '',
        couleur         TEXT NOT NULL DEFAULT '#CCE0F4',
        marque          TEXT NOT NULL DEFAULT '',
        modele          TEXT NOT NULL DEFAULT '',
        numero_serie    TEXT NOT NULL DEFAULT '',
        date_achat      TEXT,
        prix_chf        REAL,
        fournisseur     TEXT NOT NULL DEFAULT '',
        fin_garantie    TEXT,
        notes           TEXT NOT NULL DEFAULT '',
        statut          TEXT NOT NULL DEFAULT 'actif'
                        CHECK (statut IN ('actif', 'reparation', 'perdu', 'reforme')),
        photo           TEXT,
        parent_id       INTEGER REFERENCES article(id) ON DELETE SET NULL,
        cree_le         TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        modifie_le      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    CREATE INDEX article_categorie ON article(categorie_id, ordre);

    CREATE TABLE document (
        id           INTEGER PRIMARY KEY,
        article_id   INTEGER NOT NULL REFERENCES article(id) ON DELETE CASCADE,
        nom_original TEXT NOT NULL,
        fichier      TEXT NOT NULL,
        ajoute_le    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE chantier (
        id           INTEGER PRIMARY KEY,
        numero       TEXT NOT NULL DEFAULT '',
        cle_numero   TEXT NOT NULL DEFAULT '',
        nom          TEXT NOT NULL,
        responsable  TEXT NOT NULL DEFAULT '',
        facturable   INTEGER NOT NULL DEFAULT 1,
        archive      INTEGER NOT NULL DEFAULT 0,
        notes        TEXT NOT NULL DEFAULT ''
    );

    CREATE TABLE affectation (
        id           INTEGER PRIMARY KEY,
        article_id   INTEGER NOT NULL REFERENCES article(id),
        chantier_id  INTEGER NOT NULL REFERENCES chantier(id),
        date_debut   TEXT NOT NULL,
        date_fin     TEXT NOT NULL,
        responsable  TEXT NOT NULL DEFAULT '',
        remarque     TEXT NOT NULL DEFAULT '',
        CHECK (date_fin >= date_debut)
    );
    CREATE INDEX affectation_article ON affectation(article_id, date_debut);
    CREATE INDEX affectation_chantier ON affectation(chantier_id);
    """,
    # 2 : téléphone (carte SIM) et accès Swipos
    """
    ALTER TABLE article ADD COLUMN telephone TEXT NOT NULL DEFAULT '';
    ALTER TABLE article ADD COLUMN swipos_numero TEXT NOT NULL DEFAULT '';
    ALTER TABLE article ADD COLUMN swipos_mot_de_passe TEXT NOT NULL DEFAULT '';
    """,
]


def connecter():
    con = sqlite3.connect(FICHIER_BASE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def initialiser():
    """Crée le dossier de données et applique les mises à jour du schéma."""
    DOSSIER_DONNEES.mkdir(parents=True, exist_ok=True)
    (DOSSIER_FICHIERS / "photos").mkdir(parents=True, exist_ok=True)
    (DOSSIER_FICHIERS / "documents").mkdir(parents=True, exist_ok=True)
    con = connecter()
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        for numero, script in enumerate(MIGRATIONS[version:], start=version + 1):
            con.executescript(script)
            con.execute(f"PRAGMA user_version = {numero}")
        con.commit()
    finally:
        con.close()


def normaliser_numero_chantier(numero):
    """« 855325 » -> « 855 325 », « 10203 » -> « 10 203 ». Les autres écritures
    sont gardées telles quelles (espaces en trop retirés)."""
    numero = re.sub(r"\s+", " ", (numero or "").strip())
    chiffres = numero.replace(" ", "")
    if chiffres.isdigit() and len(chiffres) in (5, 6):
        return f"{chiffres[:-3]} {chiffres[-3:]}"
    return numero


def cle_numero(numero):
    """Clé de comparaison : uniquement les chiffres et lettres, en majuscules."""
    return re.sub(r"[^0-9A-Za-z]", "", numero or "").upper()
