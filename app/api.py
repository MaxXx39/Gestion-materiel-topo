"""Application Flask : pages et API JSON utilisées par l'interface."""
import datetime as dt
import json
import re
import sqlite3
import threading
import uuid
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

import base
import import_excel

DOSSIER_STATIC = Path(__file__).resolve().parent / "static"
IDENTITE = "planning-materiel-topo"
EXTENSIONS_PHOTO = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


class ErreurApi(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


# --------------------------------------------------------------------------
# Outils de validation
# --------------------------------------------------------------------------

def texte(donnees, cle, obligatoire=False, nom=None, maxi=500):
    valeur = donnees.get(cle)
    valeur = "" if valeur is None else str(valeur).strip()
    if obligatoire and not valeur:
        raise ErreurApi(f"Le champ « {nom or cle} » est obligatoire.")
    if len(valeur) > maxi:
        raise ErreurApi(f"Le champ « {nom or cle} » est trop long.")
    return valeur


def date_iso(donnees, cle, nom, obligatoire=False):
    valeur = (donnees.get(cle) or "").strip()
    if not valeur:
        if obligatoire:
            raise ErreurApi(f"La date « {nom} » est obligatoire.")
        return None
    try:
        return dt.date.fromisoformat(valeur).isoformat()
    except ValueError:
        raise ErreurApi(f"La date « {nom} » n'est pas valide.")


def montant(donnees, cle, nom):
    valeur = donnees.get(cle)
    if valeur in (None, ""):
        return None
    try:
        valeur = float(str(valeur).replace("'", "").replace(" ", "").replace(",", "."))
    except ValueError:
        raise ErreurApi(f"Le montant « {nom} » n'est pas valide.")
    if valeur < 0:
        raise ErreurApi(f"Le montant « {nom} » ne peut pas être négatif.")
    return round(valeur, 2)


def couleur(donnees, cle):
    valeur = (donnees.get(cle) or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", valeur):
        raise ErreurApi("La couleur n'est pas valide.")
    return valeur.upper()


def ligne(row):
    return dict(row) if row is not None else None


def db():
    if "con" not in g:
        g.con = base.connecter()
    return g.con


def trouver(table, ident, message):
    row = db().execute(f"SELECT * FROM {table} WHERE id = ?", (ident,)).fetchone()
    if row is None:
        raise ErreurApi(message, 404)
    return row


def aujourdhui():
    return dt.date.today().isoformat()


# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------

def creer_app():
    app = Flask(__name__, static_folder=str(DOSSIER_STATIC), static_url_path="/static")
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    @app.teardown_appcontext
    def fermer(_exc):
        con = g.pop("con", None)
        if con is not None:
            con.close()

    @app.errorhandler(ErreurApi)
    def erreur_api(e):
        return jsonify(erreur=e.message), e.code

    @app.errorhandler(HTTPException)
    def erreur_http(e):
        if request.path.startswith("/api/"):
            messages = {404: "Introuvable.", 413: "Fichier trop volumineux (200 Mo maximum)."}
            return jsonify(erreur=messages.get(e.code, e.description)), e.code
        return e

    @app.get("/api/identite")
    def identite():
        # Permet au lanceur de reconnaître cette application parmi d'autres sur le PC.
        return jsonify(application=IDENTITE)

    @app.get("/")
    def accueil():
        return send_from_directory(DOSSIER_STATIC, "index.html")

    @app.get("/fichiers/photos/<path:nom>")
    def photo(nom):
        return send_from_directory(base.DOSSIER_FICHIERS / "photos", nom)

    enregistrer_categories(app)
    enregistrer_articles(app)
    enregistrer_chantiers(app)
    enregistrer_preremplissage(app)
    enregistrer_affectations(app)
    return app


# --------------------------------------------------------------------------
# Catégories
# --------------------------------------------------------------------------

def enregistrer_categories(app):
    @app.get("/api/categories")
    def categories_liste():
        rows = db().execute(
            """SELECT c.*, (SELECT COUNT(*) FROM article a WHERE a.categorie_id = c.id) AS nb_articles
               FROM categorie c ORDER BY c.ordre, c.id"""
        ).fetchall()
        return jsonify([ligne(r) for r in rows])

    @app.post("/api/categories")
    def categories_creer():
        d = request.get_json(force=True)
        nom = texte(d, "nom", True, "Nom", 100)
        con = db()
        if con.execute("SELECT 1 FROM categorie WHERE nom = ?", (nom,)).fetchone():
            raise ErreurApi(f"La catégorie « {nom} » existe déjà.")
        ordre = con.execute("SELECT COALESCE(MAX(ordre), 0) + 1 FROM categorie").fetchone()[0]
        cur = con.execute("INSERT INTO categorie (nom, ordre) VALUES (?, ?)", (nom, ordre))
        con.commit()
        return jsonify(ligne(trouver("categorie", cur.lastrowid, ""))), 201

    @app.put("/api/categories/<int:ident>")
    def categories_modifier(ident):
        trouver("categorie", ident, "Catégorie introuvable.")
        d = request.get_json(force=True)
        nom = texte(d, "nom", True, "Nom", 100)
        con = db()
        if con.execute("SELECT 1 FROM categorie WHERE nom = ? AND id <> ?", (nom, ident)).fetchone():
            raise ErreurApi(f"La catégorie « {nom} » existe déjà.")
        con.execute("UPDATE categorie SET nom = ? WHERE id = ?", (nom, ident))
        con.commit()
        return jsonify(ligne(trouver("categorie", ident, "")))

    @app.delete("/api/categories/<int:ident>")
    def categories_supprimer(ident):
        trouver("categorie", ident, "Catégorie introuvable.")
        con = db()
        if con.execute("SELECT 1 FROM article WHERE categorie_id = ?", (ident,)).fetchone():
            raise ErreurApi("Cette catégorie contient des articles : déplacez-les d'abord dans une autre catégorie.", 409)
        con.execute("DELETE FROM categorie WHERE id = ?", (ident,))
        con.commit()
        return jsonify(ok=True)

    @app.post("/api/categories/<int:ident>/deplacer")
    def categories_deplacer(ident):
        sens = int(request.get_json(force=True).get("sens", 0))
        deplacer(db(), "categorie", ident, sens, None)
        return jsonify(ok=True)


def deplacer(con, table, ident, sens, filtre_categorie):
    """Monte (sens = -1) ou descend (sens = +1) un élément dans sa liste."""
    if filtre_categorie is None:
        rows = con.execute(f"SELECT id FROM {table} ORDER BY ordre, id").fetchall()
    else:
        rows = con.execute(
            f"SELECT id FROM {table} WHERE categorie_id = ? ORDER BY ordre, id", (filtre_categorie,)
        ).fetchall()
    ids = [r["id"] for r in rows]
    if ident not in ids:
        raise ErreurApi("Élément introuvable.", 404)
    i = ids.index(ident)
    j = i + (1 if sens > 0 else -1)
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
    for ordre, x in enumerate(ids, start=1):
        con.execute(f"UPDATE {table} SET ordre = ? WHERE id = ?", (ordre, x))
    con.commit()


# --------------------------------------------------------------------------
# Articles
# --------------------------------------------------------------------------

REQUETE_ARTICLES = """
    SELECT a.*, c.nom AS categorie_nom, c.ordre AS categorie_ordre,
           (SELECT COUNT(*) FROM document d WHERE d.article_id = a.id) AS nb_documents,
           p.numero_interne AS parent_numero,
           af.id AS aff_id, af.date_debut AS aff_debut, af.date_fin AS aff_fin,
           ch.id AS aff_chantier_id, ch.numero AS aff_chantier_numero, ch.nom AS aff_chantier_nom,
           COALESCE(NULLIF(af.responsable, ''), ch.responsable) AS aff_responsable
    FROM article a
    JOIN categorie c ON c.id = a.categorie_id
    LEFT JOIN article p ON p.id = a.parent_id
    LEFT JOIN affectation af ON af.article_id = a.id AND ? BETWEEN af.date_debut AND af.date_fin
    LEFT JOIN chantier ch ON ch.id = af.chantier_id
"""


def article_dict(row):
    d = ligne(row)
    aff = None
    if d.pop("aff_id") is not None:
        aff = {
            "date_debut": d["aff_debut"],
            "date_fin": d["aff_fin"],
            "chantier_id": d["aff_chantier_id"],
            "chantier_numero": d["aff_chantier_numero"],
            "chantier_nom": d["aff_chantier_nom"],
            "responsable": d["aff_responsable"],
        }
    for cle in ("aff_debut", "aff_fin", "aff_chantier_id", "aff_chantier_numero", "aff_chantier_nom", "aff_responsable"):
        d.pop(cle)
    d["aujourdhui"] = aff
    return d


def lire_article(donnees):
    d = donnees
    statut = d.get("statut") or "actif"
    if statut not in base.STATUTS:
        raise ErreurApi("Statut inconnu.")
    try:
        categorie_id = int(d.get("categorie_id"))
    except (TypeError, ValueError):
        raise ErreurApi("Choisissez une catégorie.")
    trouver("categorie", categorie_id, "Catégorie introuvable.")
    parent_id = d.get("parent_id") or None
    if parent_id is not None:
        parent_id = int(parent_id)
        trouver("article", parent_id, "Article principal introuvable.")
    return {
        "categorie_id": categorie_id,
        "numero_interne": texte(d, "numero_interne", True, "N° interne", 100),
        "designation": texte(d, "designation", False, "Désignation", 200),
        "code_compta": texte(d, "code_compta", False, "Code compta", 50),
        "couleur": couleur(d, "couleur"),
        "marque": texte(d, "marque", False, "Marque", 100),
        "modele": texte(d, "modele", False, "Modèle", 100),
        "numero_serie": texte(d, "numero_serie", False, "N° de série", 100),
        "date_achat": date_iso(d, "date_achat", "Date d'achat"),
        "prix_chf": montant(d, "prix_chf", "Prix"),
        "fournisseur": texte(d, "fournisseur", False, "Fournisseur", 200),
        "fin_garantie": date_iso(d, "fin_garantie", "Fin de garantie"),
        "notes": texte(d, "notes", False, "Notes", 5000),
        "statut": statut,
        "parent_id": parent_id,
    }


def verifier_numero_unique(con, numero, ident=None):
    row = con.execute(
        "SELECT id FROM article WHERE numero_interne = ? AND id IS NOT ?", (numero, ident)
    ).fetchone()
    if row:
        raise ErreurApi(f"Le n° interne « {numero} » est déjà utilisé par un autre article.")


def enregistrer_articles(app):
    @app.get("/api/articles")
    def articles_liste():
        rows = db().execute(
            REQUETE_ARTICLES + " ORDER BY c.ordre, c.id, a.ordre, a.id", (aujourdhui(),)
        ).fetchall()
        return jsonify([article_dict(r) for r in rows])

    @app.get("/api/articles/<int:ident>")
    def articles_detail(ident):
        con = db()
        row = con.execute(REQUETE_ARTICLES + " WHERE a.id = ?", (aujourdhui(), ident)).fetchone()
        if row is None:
            raise ErreurApi("Article introuvable.", 404)
        article = article_dict(row)
        article["documents"] = [ligne(r) for r in con.execute(
            "SELECT id, nom_original, ajoute_le FROM document WHERE article_id = ? ORDER BY id", (ident,))]
        article["historique"] = [ligne(r) for r in con.execute(
            """SELECT af.id, af.date_debut, af.date_fin, af.remarque,
                      COALESCE(NULLIF(af.responsable, ''), ch.responsable) AS responsable,
                      ch.id AS chantier_id, ch.numero AS chantier_numero, ch.nom AS chantier_nom
               FROM affectation af JOIN chantier ch ON ch.id = af.chantier_id
               WHERE af.article_id = ? ORDER BY af.date_debut DESC""", (ident,))]
        article["accessoires"] = [ligne(r) for r in con.execute(
            "SELECT id, numero_interne, designation, statut FROM article WHERE parent_id = ? ORDER BY numero_interne",
            (ident,))]
        return jsonify(article)

    @app.post("/api/articles")
    def articles_creer():
        a = lire_article(request.get_json(force=True))
        con = db()
        verifier_numero_unique(con, a["numero_interne"])
        a["ordre"] = con.execute(
            "SELECT COALESCE(MAX(ordre), 0) + 1 FROM article WHERE categorie_id = ?", (a["categorie_id"],)
        ).fetchone()[0]
        cols = ", ".join(a)
        cur = con.execute(f"INSERT INTO article ({cols}) VALUES ({', '.join('?' * len(a))})", list(a.values()))
        con.commit()
        return jsonify(id=cur.lastrowid), 201

    @app.put("/api/articles/<int:ident>")
    def articles_modifier(ident):
        ancien = trouver("article", ident, "Article introuvable.")
        a = lire_article(request.get_json(force=True))
        if a["parent_id"] == ident:
            raise ErreurApi("Un article ne peut pas être son propre accessoire.")
        con = db()
        verifier_numero_unique(con, a["numero_interne"], ident)
        if a["categorie_id"] != ancien["categorie_id"]:
            a["ordre"] = con.execute(
                "SELECT COALESCE(MAX(ordre), 0) + 1 FROM article WHERE categorie_id = ?", (a["categorie_id"],)
            ).fetchone()[0]
        sets = ", ".join(f"{k} = ?" for k in a)
        con.execute(
            f"UPDATE article SET {sets}, modifie_le = datetime('now', 'localtime') WHERE id = ?",
            [*a.values(), ident],
        )
        con.commit()
        return jsonify(id=ident)

    @app.delete("/api/articles/<int:ident>")
    def articles_supprimer(ident):
        article = trouver("article", ident, "Article introuvable.")
        con = db()
        if con.execute("SELECT 1 FROM affectation WHERE article_id = ?", (ident,)).fetchone():
            raise ErreurApi(
                "Cet article a un historique d'affectations. Pour le retirer du parc sans perdre "
                "l'historique, passez-le en statut « Réformé / vendu ».", 409)
        fichiers = [r["fichier"] for r in con.execute("SELECT fichier FROM document WHERE article_id = ?", (ident,))]
        con.execute("DELETE FROM article WHERE id = ?", (ident,))
        con.commit()
        if article["photo"]:
            supprimer_fichier("photos", article["photo"])
        for f in fichiers:
            supprimer_fichier("documents", f)
        return jsonify(ok=True)

    @app.post("/api/articles/<int:ident>/deplacer")
    def articles_deplacer(ident):
        article = trouver("article", ident, "Article introuvable.")
        sens = int(request.get_json(force=True).get("sens", 0))
        deplacer(db(), "article", ident, sens, article["categorie_id"])
        return jsonify(ok=True)

    @app.post("/api/articles/<int:ident>/photo")
    def articles_photo(ident):
        article = trouver("article", ident, "Article introuvable.")
        fichier = request.files.get("fichier")
        if not fichier or not fichier.filename:
            raise ErreurApi("Aucun fichier reçu.")
        ext = Path(fichier.filename).suffix.lower()
        if ext not in EXTENSIONS_PHOTO:
            raise ErreurApi("La photo doit être une image (jpg, png, gif, webp).")
        nom = f"{uuid.uuid4().hex}{ext}"
        fichier.save(base.DOSSIER_FICHIERS / "photos" / nom)
        con = db()
        con.execute("UPDATE article SET photo = ? WHERE id = ?", (nom, ident))
        con.commit()
        if article["photo"]:
            supprimer_fichier("photos", article["photo"])
        return jsonify(photo=nom)

    @app.delete("/api/articles/<int:ident>/photo")
    def articles_photo_supprimer(ident):
        article = trouver("article", ident, "Article introuvable.")
        con = db()
        con.execute("UPDATE article SET photo = NULL WHERE id = ?", (ident,))
        con.commit()
        if article["photo"]:
            supprimer_fichier("photos", article["photo"])
        return jsonify(ok=True)

    @app.post("/api/articles/<int:ident>/documents")
    def articles_documents(ident):
        trouver("article", ident, "Article introuvable.")
        fichiers = [f for f in request.files.getlist("fichiers") if f and f.filename]
        if not fichiers:
            raise ErreurApi("Aucun fichier reçu.")
        con = db()
        for f in fichiers:
            nom_sur = secure_filename(f.filename) or "document"
            nom = f"{uuid.uuid4().hex[:12]}_{nom_sur}"
            f.save(base.DOSSIER_FICHIERS / "documents" / nom)
            con.execute("INSERT INTO document (article_id, nom_original, fichier) VALUES (?, ?, ?)",
                        (ident, f.filename, nom))
        con.commit()
        return jsonify(ok=True), 201

    @app.get("/api/documents/<int:ident>")
    def documents_ouvrir(ident):
        doc = trouver("document", ident, "Document introuvable.")
        return send_from_directory(base.DOSSIER_FICHIERS / "documents", doc["fichier"],
                                   download_name=doc["nom_original"])

    @app.delete("/api/documents/<int:ident>")
    def documents_supprimer(ident):
        doc = trouver("document", ident, "Document introuvable.")
        con = db()
        con.execute("DELETE FROM document WHERE id = ?", (ident,))
        con.commit()
        supprimer_fichier("documents", doc["fichier"])
        return jsonify(ok=True)


def supprimer_fichier(sous_dossier, nom):
    chemin = base.DOSSIER_FICHIERS / sous_dossier / nom
    try:
        chemin.unlink()
    except FileNotFoundError:
        pass


# --------------------------------------------------------------------------
# Chantiers
# --------------------------------------------------------------------------

def lire_chantier(d):
    numero = base.normaliser_numero_chantier(texte(d, "numero", False, "N° de chantier", 50))
    return {
        "numero": numero,
        "cle_numero": base.cle_numero(numero),
        "nom": texte(d, "nom", True, "Nom", 200),
        "responsable": texte(d, "responsable", False, "Responsable", 100),
        "facturable": 1 if d.get("facturable", True) else 0,
        "archive": 1 if d.get("archive", False) else 0,
        "notes": texte(d, "notes", False, "Notes", 5000),
    }


def verifier_chantier_unique(con, c, ident=None):
    if c["cle_numero"]:
        row = con.execute("SELECT numero, nom FROM chantier WHERE cle_numero = ? AND id IS NOT ?",
                          (c["cle_numero"], ident)).fetchone()
        if row:
            raise ErreurApi(f"Le chantier n° {row['numero']} existe déjà ({row['nom']}).")
    else:
        row = con.execute("SELECT 1 FROM chantier WHERE cle_numero = '' AND nom = ? COLLATE NOCASE AND id IS NOT ?",
                          (c["nom"], ident)).fetchone()
        if row:
            raise ErreurApi(f"Un chantier sans numéro nommé « {c['nom']} » existe déjà.")


def enregistrer_chantiers(app):
    @app.get("/api/chantiers")
    def chantiers_liste():
        rows = db().execute(
            """SELECT ch.*, (SELECT COUNT(*) FROM affectation af WHERE af.chantier_id = ch.id) AS nb_affectations,
                      (SELECT MAX(date_fin) FROM affectation af WHERE af.chantier_id = ch.id) AS derniere_date
               FROM chantier ch ORDER BY ch.archive, ch.cle_numero = '', ch.numero, ch.nom"""
        ).fetchall()
        return jsonify([ligne(r) for r in rows])

    @app.post("/api/chantiers")
    def chantiers_creer():
        c = lire_chantier(request.get_json(force=True))
        con = db()
        verifier_chantier_unique(con, c)
        cur = con.execute(f"INSERT INTO chantier ({', '.join(c)}) VALUES ({', '.join('?' * len(c))})",
                          list(c.values()))
        con.commit()
        return jsonify(ligne(trouver("chantier", cur.lastrowid, ""))), 201

    @app.put("/api/chantiers/<int:ident>")
    def chantiers_modifier(ident):
        trouver("chantier", ident, "Chantier introuvable.")
        c = lire_chantier(request.get_json(force=True))
        con = db()
        verifier_chantier_unique(con, c, ident)
        con.execute(f"UPDATE chantier SET {', '.join(f'{k} = ?' for k in c)} WHERE id = ?", [*c.values(), ident])
        con.commit()
        return jsonify(ligne(trouver("chantier", ident, "")))

    @app.delete("/api/chantiers/<int:ident>")
    def chantiers_supprimer(ident):
        trouver("chantier", ident, "Chantier introuvable.")
        con = db()
        if con.execute("SELECT 1 FROM affectation WHERE chantier_id = ?", (ident,)).fetchone():
            raise ErreurApi("Ce chantier a des affectations. Archivez-le plutôt : il disparaîtra des listes "
                            "de choix mais restera dans l'historique.", 409)
        con.execute("DELETE FROM chantier WHERE id = ?", (ident,))
        con.commit()
        return jsonify(ok=True)


# --------------------------------------------------------------------------
# Pré-remplissage depuis l'ancien Excel (articles, catégories, chantiers)
# --------------------------------------------------------------------------

def enregistrer_preremplissage(app):
    @app.post("/api/preremplissage/analyse")
    def preremplissage_analyse():
        fichier = request.files.get("fichier")
        if not fichier or not fichier.filename:
            raise ErreurApi("Aucun fichier reçu.")
        try:
            resultat = import_excel.lire_classeur(fichier.stream)
        except import_excel.ErreurImport as e:
            raise ErreurApi(str(e))
        con = db()
        numeros = {r[0].lower() for r in con.execute("SELECT numero_interne FROM article")}
        cles = {r[0] for r in con.execute("SELECT cle_numero FROM chantier WHERE cle_numero <> ''")}
        noms = {r[0].lower() for r in con.execute("SELECT nom FROM chantier WHERE cle_numero = ''")}
        for a in resultat["articles"]:
            a["existe"] = a["numero_interne"].lower() in numeros
        for c in resultat["chantiers"]:
            cle = base.cle_numero(c["numero"])
            c["existe"] = cle in cles if cle else c["nom"].lower() in noms
        return jsonify(resultat)

    @app.post("/api/preremplissage/valider")
    def preremplissage_valider():
        d = request.get_json(force=True)
        con = db()
        compte = {"categories": 0, "articles": 0, "chantiers": 0, "ignores": 0}
        try:
            for brut in d.get("articles", []):
                nom_cat = texte(brut, "categorie", True, "Catégorie", 100)
                row = con.execute("SELECT id FROM categorie WHERE nom = ?", (nom_cat,)).fetchone()
                if row:
                    cat_id = row["id"]
                else:
                    ordre = con.execute("SELECT COALESCE(MAX(ordre), 0) + 1 FROM categorie").fetchone()[0]
                    cat_id = con.execute("INSERT INTO categorie (nom, ordre) VALUES (?, ?)", (nom_cat, ordre)).lastrowid
                    compte["categories"] += 1
                numero = texte(brut, "numero_interne", True, "N° interne", 100)
                if con.execute("SELECT 1 FROM article WHERE numero_interne = ?", (numero,)).fetchone():
                    compte["ignores"] += 1
                    continue
                ordre = con.execute("SELECT COALESCE(MAX(ordre), 0) + 1 FROM article WHERE categorie_id = ?",
                                    (cat_id,)).fetchone()[0]
                con.execute(
                    "INSERT INTO article (categorie_id, ordre, numero_interne, code_compta, couleur) VALUES (?, ?, ?, ?, ?)",
                    (cat_id, ordre, numero, texte(brut, "code_compta", False, "Code compta", 50), couleur(brut, "couleur")))
                compte["articles"] += 1
            for brut in d.get("chantiers", []):
                c = lire_chantier({"numero": brut.get("numero"), "nom": brut.get("nom"), "facturable": True})
                try:
                    verifier_chantier_unique(con, c)
                except ErreurApi:
                    compte["ignores"] += 1
                    continue
                con.execute(f"INSERT INTO chantier ({', '.join(c)}) VALUES ({', '.join('?' * len(c))})",
                            list(c.values()))
                compte["chantiers"] += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
        return jsonify(compte)


# --------------------------------------------------------------------------
# Affectations (planning)
# --------------------------------------------------------------------------

REQUETE_AFFECTATIONS = """
    SELECT af.*, ch.numero AS chantier_numero, ch.nom AS chantier_nom,
           ch.responsable AS chantier_responsable, ch.facturable AS chantier_facturable
    FROM affectation af JOIN chantier ch ON ch.id = af.chantier_id
"""

# Pile d'annulation (Ctrl+Z) : copies de la table des affectations avant chaque
# modification. Gardée en mémoire : elle repart à zéro à chaque lancement.
PILE_ANNULATION = []
VERROU = threading.Lock()
TAILLE_PILE = 30


def memoriser(con):
    rows = [ligne(r) for r in con.execute("SELECT * FROM affectation")]
    with VERROU:
        PILE_ANNULATION.append(json.dumps(rows))
        del PILE_ANNULATION[:-TAILLE_PILE]


def jour(iso, decalage):
    return (dt.date.fromisoformat(iso) + dt.timedelta(days=decalage)).isoformat()


def chevauchements(con, article_id, debut, fin, exclure=None):
    return [ligne(r) for r in con.execute(
        REQUETE_AFFECTATIONS + " WHERE af.article_id = ? AND af.date_debut <= ? AND af.date_fin >= ? AND af.id IS NOT ?"
        " ORDER BY af.date_debut", (article_id, fin, debut, exclure))]


def resoudre_chevauchements(con, conflits, debut, fin, mode):
    """mode « remplacer » : supprime les affectations en conflit.
    mode « couper » : garde leurs parties avant et après la nouvelle période."""
    for x in conflits:
        con.execute("DELETE FROM affectation WHERE id = ?", (x["id"],))
        if mode != "couper":
            continue
        morceaux = []
        if x["date_debut"] < debut:
            morceaux.append((x["date_debut"], jour(debut, -1)))
        if x["date_fin"] > fin:
            morceaux.append((jour(fin, 1), x["date_fin"]))
        for d, f in morceaux:
            con.execute(
                "INSERT INTO affectation (article_id, chantier_id, date_debut, date_fin, responsable, remarque)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (x["article_id"], x["chantier_id"], d, f, x["responsable"], x["remarque"]))


def lire_affectation(d):
    try:
        article_id, chantier_id = int(d.get("article_id")), int(d.get("chantier_id"))
    except (TypeError, ValueError):
        raise ErreurApi("Choisissez un article et un chantier.")
    trouver("article", article_id, "Article introuvable.")
    trouver("chantier", chantier_id, "Chantier introuvable.")
    debut = date_iso(d, "date_debut", "Du", True)
    fin = date_iso(d, "date_fin", "Au", True)
    if fin < debut:
        raise ErreurApi("La date de fin doit être après la date de début.")
    return {
        "article_id": article_id, "chantier_id": chantier_id, "date_debut": debut, "date_fin": fin,
        "responsable": texte(d, "responsable", False, "Responsable", 100),
        "remarque": texte(d, "remarque", False, "Remarque", 1000),
    }


def poser(con, a, ident, mode):
    """Crée (ident None) ou modifie une affectation en gérant les chevauchements."""
    conflits = chevauchements(con, a["article_id"], a["date_debut"], a["date_fin"], ident)
    if conflits and mode not in ("remplacer", "couper"):
        raise ErreurChevauchement(conflits)
    memoriser(con)
    resoudre_chevauchements(con, conflits, a["date_debut"], a["date_fin"], mode)
    if ident is None:
        ident = con.execute(f"INSERT INTO affectation ({', '.join(a)}) VALUES ({', '.join('?' * len(a))})",
                            list(a.values())).lastrowid
    else:
        con.execute(f"UPDATE affectation SET {', '.join(f'{k} = ?' for k in a)} WHERE id = ?", [*a.values(), ident])
    con.commit()
    return ident


class ErreurChevauchement(ErreurApi):
    def __init__(self, conflits):
        super().__init__("Cet article est déjà affecté sur cette période.", 409)
        self.conflits = conflits


def affectation_dict(con, ident):
    return ligne(con.execute(REQUETE_AFFECTATIONS + " WHERE af.id = ?", (ident,)).fetchone())


def enregistrer_affectations(app):
    @app.errorhandler(ErreurChevauchement)
    def erreur_chevauchement(e):
        return jsonify(erreur=e.message, chevauchement=True, conflits=e.conflits), 409

    @app.get("/api/affectations")
    def affectations_liste():
        debut = request.args.get("debut") or "0000-01-01"
        fin = request.args.get("fin") or "9999-12-31"
        rows = db().execute(REQUETE_AFFECTATIONS + " WHERE af.date_fin >= ? AND af.date_debut <= ?"
                            " ORDER BY af.article_id, af.date_debut", (debut, fin)).fetchall()
        with VERROU:
            annulable = bool(PILE_ANNULATION)
        return jsonify(affectations=[ligne(r) for r in rows], annulable=annulable)

    @app.post("/api/affectations")
    def affectations_creer():
        d = request.get_json(force=True)
        con = db()
        ident = poser(con, lire_affectation(d), None, d.get("conflit"))
        return jsonify(affectation_dict(con, ident)), 201

    @app.put("/api/affectations/<int:ident>")
    def affectations_modifier(ident):
        trouver("affectation", ident, "Affectation introuvable.")
        d = request.get_json(force=True)
        con = db()
        poser(con, lire_affectation(d), ident, d.get("conflit"))
        return jsonify(affectation_dict(con, ident))

    @app.delete("/api/affectations/<int:ident>")
    def affectations_supprimer(ident):
        trouver("affectation", ident, "Affectation introuvable.")
        con = db()
        memoriser(con)
        con.execute("DELETE FROM affectation WHERE id = ?", (ident,))
        con.commit()
        return jsonify(ok=True)

    @app.post("/api/affectations/<int:ident>/rendre")
    def affectations_rendre(ident):
        """Rendre au dépôt : la date donnée devient le dernier jour sur le chantier."""
        af = trouver("affectation", ident, "Affectation introuvable.")
        date = date_iso(request.get_json(force=True), "date", "Dernier jour", True)
        if date < af["date_debut"]:
            raise ErreurApi("Le dernier jour ne peut pas être avant le début de l'affectation.")
        if date >= af["date_fin"]:
            raise ErreurApi("L'affectation se termine déjà à cette date ou avant.")
        con = db()
        memoriser(con)
        con.execute("UPDATE affectation SET date_fin = ? WHERE id = ?", (date, ident))
        con.commit()
        return jsonify(affectation_dict(con, ident))

    @app.post("/api/affectations/<int:ident>/couper")
    def affectations_couper(ident):
        """Coupe en deux : [début, date - 1] et [date, fin]. Avec « chantier_id », la seconde
        partie part sur un autre chantier (« changer de chantier à partir du… »)."""
        af = trouver("affectation", ident, "Affectation introuvable.")
        d = request.get_json(force=True)
        date = date_iso(d, "date", "À partir du", True)
        if not (af["date_debut"] < date <= af["date_fin"]):
            raise ErreurApi("Une affectation d'un seul jour ne peut pas être coupée."
                            if af["date_debut"] == af["date_fin"] else
                            "La date doit être après le premier jour de l'affectation, et au plus tard son dernier jour.")
        chantier_id = af["chantier_id"]
        responsable = af["responsable"]
        if d.get("chantier_id"):
            chantier_id = int(d["chantier_id"])
            trouver("chantier", chantier_id, "Chantier introuvable.")
            responsable = texte(d, "responsable", False, "Responsable", 100)
        con = db()
        memoriser(con)
        con.execute("UPDATE affectation SET date_fin = ? WHERE id = ?", (jour(date, -1), ident))
        nouvel = con.execute(
            "INSERT INTO affectation (article_id, chantier_id, date_debut, date_fin, responsable, remarque)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (af["article_id"], chantier_id, date, af["date_fin"], responsable, af["remarque"])).lastrowid
        con.commit()
        return jsonify(affectation_dict(con, nouvel)), 201

    @app.post("/api/annuler")
    def annuler():
        with VERROU:
            if not PILE_ANNULATION:
                raise ErreurApi("Rien à annuler.")
            rows = json.loads(PILE_ANNULATION.pop())
        con = db()
        try:
            con.execute("DELETE FROM affectation")
            for r in rows:
                con.execute(f"INSERT INTO affectation ({', '.join(r)}) VALUES ({', '.join('?' * len(r))})",
                            list(r.values()))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise ErreurApi("Annulation impossible : un article ou un chantier concerné a été supprimé entre-temps.")
        return jsonify(ok=True)
