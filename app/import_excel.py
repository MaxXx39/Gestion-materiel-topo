"""Lecture de l'ancien planning Excel (GESTION_GPS_V2.xlsx).

Structure attendue (une seule feuille) :
- ligne 2 : dates, à partir de la colonne D ;
- à partir de la ligne 4 : colonne A = catégorie (cellules fusionnées en vertical),
  colonne B = code compta, colonne C = n° interne (sa couleur de fond = couleur de l'article) ;
- affectations = cellules fusionnées horizontalement, texte « n° chantier – nom – responsable ».
"""
import colorsys
import datetime as dt
import re
from collections import OrderedDict
from xml.etree import ElementTree

import openpyxl

import base

LIGNE_DEBUT = 4
COLONNE_JOURS = 4  # colonne D
NS_THEME = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
ORDRE_THEME = ["lt1", "dk1", "lt2", "dk2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]

RE_NUMERO = re.compile(r"^\s*(\d{2,3}\s\d{3}|\d{4,6})(?!\d)\s*[-–]?\s*(.*)$")
RE_SEPARATEUR = re.compile(r"\s+[-–]\s+")


class ErreurImport(Exception):
    pass


# ---------------------------------------------------------------- Couleurs

def couleurs_theme(classeur):
    try:
        racine = ElementTree.fromstring(classeur.loaded_theme)
        schema = racine.find(".//a:clrScheme", NS_THEME)
        couleurs = []
        for nom in ORDRE_THEME:
            e = schema.find(f"a:{nom}", NS_THEME)[0]
            couleurs.append(e.get("lastClr") or e.get("val"))
        return couleurs
    except Exception:
        return None


def appliquer_teinte(hexa, teinte):
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = l * (1 + teinte) if teinte < 0 else l * (1 - teinte) + teinte
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02X%02X%02X" % tuple(round(x * 255) for x in (r, g, b))


def couleur_cellule(cellule, theme):
    remplissage = cellule.fill
    if remplissage is None or remplissage.fill_type is None:
        return None
    c = remplissage.fgColor
    if c.type == "rgb" and isinstance(c.rgb, str) and len(c.rgb) == 8:
        return "#" + c.rgb[2:].upper()
    if c.type == "theme" and theme and c.theme is not None and c.theme < len(theme):
        return appliquer_teinte(theme[c.theme], c.tint or 0)
    return None


# ---------------------------------------------------------------- Chantiers

def decouper_texte(texte):
    """« 123 456 Ville - M Dupont » -> (« 123 456 », « Ville », certain ?)."""
    texte = re.sub(r"\s+", " ", str(texte)).strip()
    m = RE_NUMERO.match(texte)
    if not m:
        # Pas de numéro (ex. « RONCHI », « GEOMETRE - MGO ») : tout le texte devient le nom.
        return "", texte, False
    numero = base.normaliser_numero_chantier(m.group(1))
    reste = m.group(2).strip(" -–")
    morceaux = RE_SEPARATEUR.split(reste)
    if len(morceaux) >= 2:
        nom = " - ".join(morceaux[:-1])
        dernier = morceaux[-1]
        # Le dernier morceau ressemble-t-il à une personne (1 ou 2 mots, sans chiffre) ?
        certain = not re.search(r"\d", dernier) and len(dernier.split()) <= 2
        return numero, nom, certain
    # Pas de tiret : impossible de savoir si la fin du texte est un responsable.
    return numero, reste, False


# ---------------------------------------------------------------- Lecture

def lire_classeur(chemin_ou_fichier):
    try:
        classeur = openpyxl.load_workbook(chemin_ou_fichier)
    except Exception:
        raise ErreurImport("Ce fichier n'a pas pu être lu. Choisissez le fichier Excel (.xlsx) du planning.")
    feuille = classeur.worksheets[0]
    theme = couleurs_theme(classeur)

    fusions = list(feuille.merged_cells.ranges)
    # Étendue verticale des catégories (colonne A).
    etendue_categorie = {}
    for f in fusions:
        if f.min_col == 1 and f.min_row >= LIGNE_DEBUT:
            etendue_categorie[f.min_row] = f.max_row

    categories = []
    articles = []
    lignes_articles = set()
    lignes_numero = {}
    categorie, fin_categorie, compteur_vides = None, 0, 0
    for r in range(LIGNE_DEBUT, feuille.max_row + 1):
        valeur_a = feuille.cell(r, 1).value
        if valeur_a not in (None, ""):
            categorie = re.sub(r"\s+", " ", str(valeur_a)).strip()
            fin_categorie = etendue_categorie.get(r, r)
            compteur_vides = 0
            if categorie not in categories:
                categories.append(categorie)
        if categorie is None or r > fin_categorie:
            continue
        numero = feuille.cell(r, 3).value
        code = feuille.cell(r, 2).value
        couleur = couleur_cellule(feuille.cell(r, 3), theme) or couleur_cellule(feuille.cell(r, 2), theme)
        if numero in (None, ""):
            # Ligne vide dans une catégorie (ex. guidage 3D) : article provisoire numéroté.
            compteur_vides += 1
            numero = f"{categorie.title()} {compteur_vides}"
        if isinstance(code, float) and code.is_integer():
            code = int(code)
        lignes_numero[r] = re.sub(r"\s+", " ", str(numero)).strip()
        articles.append({
            "categorie": categorie,
            "numero_interne": re.sub(r"\s+", " ", str(numero)).strip(),
            "code_compta": "" if code is None else str(code).strip(),
            "couleur": couleur or "#FFFFFF",
        })
        lignes_articles.add(r)

    if not articles:
        raise ErreurImport("Aucun article trouvé : vérifiez que c'est bien le fichier du planning "
                           "(catégories en colonne A, n° interne en colonne C à partir de la ligne 4).")

    # Date du premier jour (cellule D2) : chaque colonne suivante ajoute un jour.
    premier = feuille.cell(2, COLONNE_JOURS).value
    if isinstance(premier, dt.datetime):
        premier = premier.date()
    if not isinstance(premier, dt.date):
        premier = None

    # Barres : cellules fusionnées et cellules isolées dans la zone des jours.
    segments = []
    deja = set()
    for f in fusions:
        if f.min_row in lignes_articles and f.min_col >= COLONNE_JOURS:
            v = feuille.cell(f.min_row, f.min_col).value
            for r in range(f.min_row, f.max_row + 1):
                for c in range(f.min_col, f.max_col + 1):
                    deja.add((r, c))
            if v not in (None, ""):
                segments.append([f.min_row, f.min_col, f.max_col, re.sub(r"\s+", " ", str(v)).strip()])
    for r in lignes_articles:
        for c in range(COLONNE_JOURS, feuille.max_column + 1):
            if (r, c) in deja:
                continue
            v = feuille.cell(r, c).value
            if v not in (None, "") and not (isinstance(v, str) and v.startswith("=")):
                segments.append([r, c, c, re.sub(r"\s+", " ", str(v)).strip()])

    # L'Excel coupe les barres à chaque fin de mois : on recolle les morceaux
    # consécutifs qui portent le même texte.
    segments.sort()
    barres = []
    for seg in segments:
        dernier = barres[-1] if barres else None
        if dernier and dernier[0] == seg[0] and dernier[2] + 1 == seg[1] and dernier[3] == seg[3]:
            dernier[2] = seg[2]
        else:
            barres.append(list(seg))

    chantiers = regrouper_chantiers([b[3] for b in barres])
    affectations = []
    if premier:
        for r, c1, c2, texte in barres:
            numero, nom, _ = decouper_texte(texte)
            affectations.append({
                "numero_interne": lignes_numero[r],
                "date_debut": (premier + dt.timedelta(days=c1 - COLONNE_JOURS)).isoformat(),
                "date_fin": (premier + dt.timedelta(days=c2 - COLONNE_JOURS)).isoformat(),
                "texte": texte,
                "cle": cle_chantier(numero, nom),
            })

    return {"categories": categories, "articles": articles, "chantiers": chantiers,
            "affectations": affectations, "dates_trouvees": premier is not None}


def cle_chantier(numero, nom):
    return base.cle_numero(numero) or "NOM:" + nom.upper()


def regrouper_chantiers(textes):
    groupes = OrderedDict()
    for texte in textes:
        texte_net = re.sub(r"\s+", " ", texte).strip()
        numero, nom, certain = decouper_texte(texte_net)
        cle = cle_chantier(numero, nom)
        g = groupes.setdefault(cle, {"cle": cle, "numero": numero, "noms": [], "textes": [], "certain": True})
        if texte_net not in g["textes"]:
            g["textes"].append(texte_net)
        g["noms"].append(nom)
        g["certain"] = g["certain"] and certain
    chantiers = []
    for g in groupes.values():
        # Nom le plus fréquent parmi les variantes d'écriture.
        noms = [n for n in g["noms"] if n] or [""]
        nom = max(dict.fromkeys(noms), key=noms.count)
        variantes = len({n.upper() for n in noms}) > 1
        chantiers.append({
            "cle": g["cle"],
            "numero": g["numero"],
            "nom": nom,
            "textes": g["textes"],
            "a_verifier": (not g["certain"]) or variantes,
        })
    chantiers.sort(key=lambda c: (c["numero"] == "", base.cle_numero(c["numero"]).zfill(8), c["nom"].upper()))
    return chantiers
