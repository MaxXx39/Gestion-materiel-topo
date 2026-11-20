"""Sauvegarde et restauration de toutes les données (base + photos + documents) dans un fichier .zip."""
import datetime as dt
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import base

NOM_BASE = "planning.db"


class ErreurSauvegarde(Exception):
    pass


def nom_sauvegarde():
    return f"sauvegarde_planning_{dt.datetime.now():%Y-%m-%d_%Hh%M}.zip"


def creer_zip(destination):
    """Écrit la sauvegarde complète dans « destination » (chemin ou fichier ouvert)."""
    with tempfile.TemporaryDirectory() as dossier:
        copie = Path(dossier) / NOM_BASE
        # Copie cohérente de la base, même si elle est en cours d'utilisation.
        source = base.connecter()
        cible = sqlite3.connect(copie)
        try:
            source.backup(cible)
        finally:
            cible.close()
            source.close()
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(copie, NOM_BASE)
            for f in sorted(base.DOSSIER_FICHIERS.rglob("*")):
                if f.is_file():
                    z.write(f, "fichiers/" + f.relative_to(base.DOSSIER_FICHIERS).as_posix())


def restaurer_zip(chemin_zip):
    """Remplace toutes les données par celles du zip. Une copie de sécurité des données
    actuelles est d'abord enregistrée dans donnees/sauvegardes_auto/."""
    try:
        z = zipfile.ZipFile(chemin_zip)
    except zipfile.BadZipFile:
        raise ErreurSauvegarde("Ce fichier n'est pas une sauvegarde valide (.zip attendu).")
    with z, tempfile.TemporaryDirectory() as dossier:
        noms = z.namelist()
        if NOM_BASE not in noms:
            raise ErreurSauvegarde("Ce fichier .zip ne contient pas de sauvegarde du planning (planning.db manquant).")
        for nom in noms:
            if nom != NOM_BASE and (not nom.startswith("fichiers/") or ".." in Path(nom).parts or nom.startswith("/")):
                raise ErreurSauvegarde("Ce fichier .zip contient des éléments inattendus : restauration refusée.")
        z.extractall(dossier)
        nouvelle_base = Path(dossier) / NOM_BASE
        try:
            con = sqlite3.connect(nouvelle_base)
            ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            con.close()
        except sqlite3.DatabaseError:
            ok, tables = False, set()
        if not ok or not {"article", "chantier", "affectation"} <= tables:
            raise ErreurSauvegarde("La base contenue dans ce fichier est illisible ou incomplète.")

        # Copie de sécurité des données actuelles.
        dossier_auto = base.DOSSIER_DONNEES / "sauvegardes_auto"
        dossier_auto.mkdir(parents=True, exist_ok=True)
        securite = dossier_auto / f"avant_restauration_{dt.datetime.now():%Y-%m-%d_%Hh%M%S}.zip"
        creer_zip(securite)

        shutil.copyfile(nouvelle_base, base.FICHIER_BASE)
        if base.DOSSIER_FICHIERS.exists():
            shutil.rmtree(base.DOSSIER_FICHIERS)
        source_fichiers = Path(dossier) / "fichiers"
        if source_fichiers.exists():
            shutil.copytree(source_fichiers, base.DOSSIER_FICHIERS)
        base.initialiser()  # recrée les dossiers manquants et met le format à jour si besoin
        return securite
