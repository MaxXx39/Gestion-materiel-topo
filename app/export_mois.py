"""Export du planning d'un mois : PDF pour la comptabilité et Excel de dépannage.

Le PDF reprend les informations du modèle d'origine (2026_10.pdf) dans une mise en page plus lisible :
A4 paysage, colonnes catégorie / code compta / n° interne / un jour par colonne, couleur propre à chaque article.
L'Excel garde la disposition de l'ancien fichier, pour pouvoir être modifié comme avant.
"""
import calendar
import datetime as dt
import io
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

MOIS = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT",
        "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]
JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]
GRIS_CODE = "#D9D9D9"

# ------------------------------------------------------------------ Police
DOSSIER_POLICES = Path(__file__).resolve().parent / "polices"
try:
    pdfmetrics.registerFont(TTFont("Carlito", str(DOSSIER_POLICES / "Carlito-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("Carlito-Gras", str(DOSSIER_POLICES / "Carlito-Bold.ttf")))
    POLICE, POLICE_GRAS = "Carlito", "Carlito-Gras"
except Exception:  # police absente : repli sur Helvetica
    POLICE, POLICE_GRAS = "Helvetica", "Helvetica-Bold"


# ------------------------------------------------------------------ Données
def donnees_mois(con, annee, mois):
    n = calendar.monthrange(annee, mois)[1]
    debut, fin = dt.date(annee, mois, 1).isoformat(), dt.date(annee, mois, n).isoformat()
    affectations = [dict(r) for r in con.execute(
        """SELECT af.*, ch.numero AS chantier_numero, ch.nom AS chantier_nom, ch.responsable AS chantier_responsable
           FROM affectation af JOIN chantier ch ON ch.id = af.chantier_id
           WHERE af.date_fin >= ? AND af.date_debut <= ? ORDER BY af.date_debut""", (debut, fin))]
    avec_affectation = {a["article_id"] for a in affectations}
    articles = [dict(r) for r in con.execute(
        """SELECT a.*, c.nom AS categorie_nom FROM article a JOIN categorie c ON c.id = a.categorie_id
           ORDER BY c.ordre, c.id, a.ordre, a.id""")]
    # Articles actifs, plus les autres s'ils ont été affectés ce mois-ci (ils doivent être facturés).
    articles = [a for a in articles if a["statut"] == "actif" or a["id"] in avec_affectation]
    groupes = []
    for a in articles:
        if groupes and groupes[-1]["id"] == a["categorie_id"]:
            groupes[-1]["articles"].append(a)
        else:
            groupes.append({"id": a["categorie_id"], "nom": a["categorie_nom"], "articles": [a]})
    for af in affectations:
        resp = af["responsable"] or af["chantier_responsable"]
        af["libelle"] = " – ".join(x for x in (af["chantier_numero"], af["chantier_nom"], resp) if x)
        af["j1"] = 1 if af["date_debut"] < debut else int(af["date_debut"][8:])
        af["j2"] = n if af["date_fin"] > fin else int(af["date_fin"][8:])
    return {"annee": annee, "mois": mois, "n": n, "groupes": groupes, "affectations": affectations}


def nom_fichier(annee, mois, extension):
    return f"{annee}_{mois:02d}.{extension}"


# ------------------------------------------------------------------ PDF
# Mise en page améliorée du modèle d'origine : mêmes informations (catégorie, code compta,
# n° interne, une colonne par jour, barres colorées « n° – chantier – responsable »),
# mais sur toute la largeur de la page, avec des textes plus grands.
MARGE = 22
H_TITRE, H_TETE, H_PIED = 30, 26, 16
L_CAT, L_CODE, L_NUM = 36, 36, 74
MIN_LIGNES_GROUPE = 3  # hauteur minimale d'une catégorie, pour que son nom reste lisible
GRIS_WE = "#ECECEC"
GRIS_CAT = "#E4E4E4"


def couper_texte(texte, police, taille, largeur):
    """Tronque avec « … » si le texte dépasse la largeur disponible."""
    if pdfmetrics.stringWidth(texte, police, taille) <= largeur:
        return texte
    while texte and pdfmetrics.stringWidth(texte + "…", police, taille) > largeur:
        texte = texte[:-1]
    return texte + "…" if texte else ""


def lignes_mots(texte, police, taille, largeur):
    """Découpe un texte en lignes qui tiennent dans la largeur donnée."""
    lignes, courante = [], ""
    for mot in texte.split():
        essai = f"{courante} {mot}".strip()
        if courante and pdfmetrics.stringWidth(essai, police, taille) > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes


def fonce(hexa, facteur=0.6):
    h = hexa.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return Color(r * facteur / 255, g * facteur / 255, b * facteur / 255)


def pdf_mois(con, annee, mois):
    d = donnees_mois(con, annee, mois)
    n = d["n"]
    tampon = io.BytesIO()
    largeur_page, hauteur_page = landscape(A4)
    c = canvas.Canvas(tampon, pagesize=(largeur_page, hauteur_page))
    c.setTitle(f"Planning du matériel – {MOIS[mois - 1]} {annee}")
    c.setAuthor("Planning du matériel topo")
    Y = lambda t: hauteur_page - t  # noqa: E731  (coordonnées « depuis le haut »)

    x0, x1 = MARGE, largeur_page - MARGE
    x_code, x_num = x0 + L_CAT, x0 + L_CAT + L_CODE
    x_jours = x_num + L_NUM
    l_jour = (x1 - x_jours) / n
    xj = lambda j: x_jours + (j - 1) * l_jour  # noqa: E731
    t_tete = MARGE + H_TITRE
    t_lignes = t_tete + H_TETE
    t_fin = hauteur_page - MARGE - H_PIED
    jours = [dt.date(annee, mois, j) for j in range(1, n + 1)]

    def trait(xa, ta, xb, tb, epaisseur, couleur=black):
        c.setStrokeColor(couleur)
        c.setLineWidth(epaisseur)
        c.line(xa, Y(ta), xb, Y(tb))

    def rect(x, t, w, h, fond):
        c.setFillColor(HexColor(fond) if isinstance(fond, str) else fond)
        c.rect(x, Y(t + h), w, h, stroke=0, fill=1)

    def triangle(x_pointe, y_milieu, sens, couleur):
        """Triangle plein ; sens -1 = pointe vers la gauche, +1 = vers la droite."""
        chemin = c.beginPath()
        chemin.moveTo(x_pointe, y_milieu)
        chemin.lineTo(x_pointe - sens * 4.5, y_milieu + 3.2)
        chemin.lineTo(x_pointe - sens * 4.5, y_milieu - 3.2)
        chemin.close()
        c.setFillColor(couleur)
        c.drawPath(chemin, stroke=0, fill=1)

    def ecrire(x, t, texte, police, taille, centre=False, couleur=black):
        c.setFillColor(couleur)
        c.setFont(police, taille)
        (c.drawCentredString if centre else c.drawString)(x, Y(t), texte)

    # ---- Titre
    ecrire(x0, MARGE + 17, f"{MOIS[mois - 1]} {annee}", POLICE_GRAS, 17)
    ecrire(x0 + pdfmetrics.stringWidth(f"{MOIS[mois - 1]} {annee}", POLICE_GRAS, 17) + 10, MARGE + 17,
           "Planning du matériel – à facturer par chantier", POLICE, 9, couleur=Color(.35, .35, .35))

    # ---- Hauteurs des lignes : chaque catégorie a au moins MIN_LIGNES_GROUPE unités.
    unites = [max(len(g["articles"]), MIN_LIGNES_GROUPE) for g in d["groupes"]] or [1]
    h_unite = (t_fin - t_lignes) / sum(unites)

    # ---- Fonds : week-ends, colonne code, en-tête
    for j, jour in enumerate(jours, start=1):
        if jour.weekday() >= 5:
            rect(xj(j), t_tete, l_jour, t_fin - t_tete, GRIS_WE)
    rect(x_code, t_tete, L_CODE, t_fin - t_tete, GRIS_CODE)
    ecrire(x_code + L_CODE / 2, t_tete + 11, "N° MS", POLICE_GRAS, 6.5, centre=True)
    ecrire(x_code + L_CODE / 2, t_tete + 19, "à facturer", POLICE, 6.5, centre=True)
    ecrire(x_num + 3, t_tete + 16, "N° interne", POLICE_GRAS, 6.5)
    for j, jour in enumerate(jours, start=1):
        xc = xj(j) + l_jour / 2
        ecrire(xc, t_tete + 11, str(j), POLICE_GRAS, 8.5, centre=True)
        ecrire(xc, t_tete + 20.5, JOURS[jour.weekday()], POLICE, 6.5, centre=True, couleur=Color(.3, .3, .3))

    # ---- Séparations des jours (sous les barres)
    for j in range(2, n + 1):
        lundi = jours[j - 1].weekday() == 0
        trait(xj(j), t_tete, xj(j), t_fin, 0.6 if lundi else 0.25, Color(.45, .45, .45) if lundi else Color(.72, .72, .72))

    # ---- Articles et barres
    par_article = {}
    for af in d["affectations"]:
        par_article.setdefault(af["article_id"], []).append(af)
    t = t_lignes
    limites = [t_lignes]
    for g, u in zip(d["groupes"], unites):
        h_ligne = h_unite * u / len(g["articles"])
        t_groupe = t
        for i, a in enumerate(g["articles"]):
            rect(x_num, t, L_NUM, h_ligne, a["couleur"])
            ecrire(x_code + L_CODE / 2, t + h_ligne / 2 + 2.8, couper_texte(a["code_compta"], POLICE, 8, L_CODE - 3),
                   POLICE, 8, centre=True)
            taille = 8.5
            while taille > 6 and pdfmetrics.stringWidth(a["numero_interne"], POLICE_GRAS, taille) > L_NUM - 5:
                taille -= 0.25
            ecrire(x_num + 3, t + h_ligne / 2 + taille / 3, couper_texte(a["numero_interne"], POLICE_GRAS, taille, L_NUM - 5),
                   POLICE_GRAS, taille)
            marge_v = min(2.2, h_ligne * 0.12)
            for af in par_article.get(a["id"], []):
                bx1, bx2 = xj(af["j1"]) + 0.8, xj(af["j2"] + 1) - 0.8
                bh = h_ligne - 2 * marge_v
                c.setFillColor(HexColor(a["couleur"]))
                c.setStrokeColor(fonce(a["couleur"]))
                c.setLineWidth(0.7)
                c.roundRect(bx1, Y(t + marge_v + bh), bx2 - bx1, bh, 2, stroke=1, fill=1)
                nb = af["j2"] - af["j1"] + 1
                milieu = Y(t + h_ligne / 2)
                avant = af["date_debut"] < jours[0].isoformat()
                apres = af["date_fin"] > jours[-1].isoformat()
                # Petit triangle en bout de barre : l'affectation continue sur le mois voisin.
                if avant:
                    triangle(bx1 + 2, milieu, -1, fonce(a["couleur"]))
                if apres:
                    triangle(bx2 - 2, milieu, 1, fonce(a["couleur"]))
                suffixe = f" · {nb} j"
                taille_b = 7 if bh >= 11 else 6
                retrait = 8 * (avant + apres)
                place = bx2 - bx1 - 4 - retrait - pdfmetrics.stringWidth(suffixe, POLICE, taille_b)
                texte = couper_texte(af["libelle"], POLICE, taille_b, place) + suffixe if place > 12 \
                    else couper_texte(f"{nb} j", POLICE, taille_b, bx2 - bx1 - 2 - retrait)
                decalage = 4 * (avant - apres)
                ecrire((bx1 + bx2) / 2 + decalage, t + h_ligne / 2 + taille_b * 0.35, texte, POLICE, taille_b, centre=True)
            t += h_ligne
            if i < len(g["articles"]) - 1:
                trait(x_code, t, x1, t, 0.3, Color(.6, .6, .6))
        # Nom de la catégorie, sur fond gris clair
        h_groupe = t - t_groupe
        rect(x0, t_groupe, L_CAT, h_groupe, GRIS_CAT)
        taille = 7.5
        lignes = lignes_mots(g["nom"], POLICE_GRAS, taille, h_groupe - 6)
        while len(lignes) * (taille + 1) > L_CAT - 4 and taille > 5:
            taille -= 0.5
            lignes = lignes_mots(g["nom"], POLICE_GRAS, taille, h_groupe - 6)
        bloc = len(lignes) * (taille + 1)
        for k, ligne in enumerate(lignes):
            w = pdfmetrics.stringWidth(ligne, POLICE_GRAS, taille)
            c.saveState()
            c.translate(x0 + L_CAT / 2 - bloc / 2 + (k + 1) * (taille + 1) - 2, Y(t_groupe + h_groupe / 2 + w / 2))
            c.rotate(90)
            c.setFillColor(black)
            c.setFont(POLICE_GRAS, taille)
            c.drawString(0, 0, ligne)
            c.restoreState()
        limites.append(t)

    # ---- Cadres
    for tg in limites:
        trait(x0, tg, x1, tg, 0.8)
    trait(x_code, t_tete, x_code, t_fin, 0.5)
    trait(x_num, t_tete, x_num, t_fin, 0.5)
    trait(x_jours, t_tete, x_jours, t_fin, 0.8)
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.rect(x0, Y(t_fin), x1 - x0, t_fin - t_tete, stroke=1, fill=0)

    # ---- Pied de page
    gris = Color(.4, .4, .4)
    triangle(x0 + 1, Y(t_fin + 9), -1, gris)
    triangle(x0 + 13, Y(t_fin + 9), 1, gris)
    ecrire(x0 + 17, t_fin + 11, "en bout de barre : l'affectation continue le mois précédent / suivant"
           "   ·   j = nombre de jours dans le mois   ·   fond gris = week-end", POLICE, 6.5, couleur=gris)
    edite = f"Édité le {dt.date.today():%d.%m.%Y}"
    c.setFont(POLICE, 6.5)
    c.setFillColor(gris)
    c.drawRightString(x1, Y(t_fin + 11), edite)

    c.showPage()
    c.save()
    return tampon.getvalue()


# ------------------------------------------------------------------ Excel
def excel_mois(con, annee, mois):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    d = donnees_mois(con, annee, mois)
    n = d["n"]
    wb = Workbook()
    ws = wb.active
    ws.title = f"{MOIS[mois - 1].capitalize()} {annee}"

    fin, moyen, fort = Side("thin", color="808080"), Side("thin"), Side("medium")
    remplir = lambda hexa: PatternFill("solid", fgColor=hexa.replace("#", "").upper())  # noqa: E731
    centre = Alignment(horizontal="center", vertical="center", wrap_text=False)
    police = Font(name="Calibri", size=9)
    derniere_col = 3 + n

    ws.column_dimensions["A"].width = 11
    ws.column_dimensions["B"].width = 6.5
    ws.column_dimensions["C"].width = 18
    for j in range(1, n + 1):
        ws.column_dimensions[get_column_letter(3 + j)].width = 3.4

    # En-tête
    ws.merge_cells(start_row=1, start_column=4, end_row=1, end_column=derniere_col)
    ws.cell(1, 4, MOIS[mois - 1]).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(1, 4).alignment = centre
    ws.row_dimensions[1].height = 14
    ws.row_dimensions[2].height = 58
    ws.row_dimensions[3].height = 22
    ws.merge_cells("B2:B3")
    b = ws["B2"]
    b.value = "N° MS - A facturer"
    b.alignment = Alignment(horizontal="center", vertical="center", text_rotation=90, wrap_text=True)
    b.fill = remplir(GRIS_CODE)
    b.font = police
    for j in range(1, n + 1):
        jour = dt.date(annee, mois, j)
        col = 3 + j
        c2 = ws.cell(2, col, jour)
        c2.number_format = "dd.mm.yyyy"
        c2.alignment = Alignment(horizontal="center", vertical="bottom", text_rotation=90)
        c2.font = Font(name="Calibri", size=7)
        c3 = ws.cell(3, col, JOURS[jour.weekday()])
        c3.alignment = Alignment(horizontal="center", vertical="bottom", text_rotation=90)
        c3.font = Font(name="Calibri", size=7)
        for r in (2, 3):
            ws.cell(r, col).border = Border(left=fin, right=fin, top=fort if r == 2 else None, bottom=fort if r == 3 else None)

    par_article = {}
    for af in d["affectations"]:
        par_article.setdefault(af["article_id"], []).append(af)

    r = 4
    for g in d["groupes"]:
        nb = len(g["articles"])
        hauteur = 15 if nb >= MIN_LIGNES_GROUPE else 15 * MIN_LIGNES_GROUPE / nb
        r_groupe = r
        for a in g["articles"]:
            ws.row_dimensions[r].height = hauteur
            code = ws.cell(r, 2, a["code_compta"] or None)
            code.fill, code.alignment, code.font = remplir(GRIS_CODE), centre, police
            num = ws.cell(r, 3, a["numero_interne"])
            num.fill, num.font = remplir(a["couleur"]), police
            num.alignment = Alignment(vertical="center")
            for col in range(2, derniere_col + 1):
                ws.cell(r, col).border = Border(left=fin if col > 3 else moyen, right=fort if col == 3 else (fin if col > 3 else moyen),
                                                top=moyen, bottom=moyen)
            for af in par_article.get(a["id"], []):
                c1, c2 = 3 + af["j1"], 3 + af["j2"]
                if c2 > c1:
                    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
                cel = ws.cell(r, c1, af["libelle"])
                cel.alignment = centre
                cel.font = Font(name="Calibri", size=8)
                for col in range(c1, c2 + 1):
                    ws.cell(r, col).fill = remplir(a["couleur"])
                    ws.cell(r, col).border = Border(top=moyen, bottom=moyen, left=moyen if col == c1 else None,
                                                    right=moyen if col == c2 else None)
            r += 1
        if r - 1 > r_groupe:
            ws.merge_cells(start_row=r_groupe, start_column=1, end_row=r - 1, end_column=1)
        cat = ws.cell(r_groupe, 1, g["nom"])
        cat.font = Font(name="Calibri", size=9, bold=True)
        cat.alignment = Alignment(horizontal="center", vertical="center", text_rotation=90, wrap_text=True)
        # Trait épais autour de chaque catégorie
        for col in range(1, derniere_col + 1):
            haut, bas = ws.cell(r_groupe, col), ws.cell(r - 1, col)
            haut.border = Border(left=haut.border.left, right=haut.border.right, top=fort, bottom=haut.border.bottom)
            bas.border = Border(left=bas.border.left, right=bas.border.right, top=bas.border.top, bottom=fort)
        for rr in range(r_groupe, r):
            ws.cell(rr, 1).border = Border(left=fort, right=moyen, top=fort if rr == r_groupe else None,
                                           bottom=fort if rr == r - 1 else None)

    # Mise en page : A4 paysage, une seule page.
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.4
    ws.print_area = f"A1:{get_column_letter(derniere_col)}{max(r - 1, 3)}"
    ws.print_options.horizontalCentered = True
    ws.freeze_panes = "D4"

    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()
