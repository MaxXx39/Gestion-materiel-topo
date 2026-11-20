"""Export du planning d'un mois : PDF pour la comptabilité et Excel de dépannage.

La mise en page reprend celle du PDF d'origine (2026_10.pdf, imprimé depuis Excel) :
A4 paysage, colonnes catégorie / code compta / n° interne / un jour par colonne,
dates et jours écrits à la verticale, couleur propre à chaque article.
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
# Géométrie mesurée sur le PDF d'origine (en points, origine en haut à gauche).
X_TABLE, X_FIN = 119.2, 721.7
L_CAT, L_CODE, L_NUM = 54.3, 34.0, 59.5
T_TABLE, T_DATES, T_CODE_TETE, T_LIGNES, T_FIN = 36.6, 45.2, 79.2, 113.9, 557.0
TRAIT_FORT, TRAIT_MOYEN, TRAIT_FIN = 0.96, 0.48, 0.2
MIN_LIGNES_GROUPE = 3  # hauteur minimale d'une catégorie, pour que son nom reste lisible


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


def pdf_mois(con, annee, mois):
    d = donnees_mois(con, annee, mois)
    tampon = io.BytesIO()
    largeur_page, hauteur_page = landscape(A4)
    c = canvas.Canvas(tampon, pagesize=(largeur_page, hauteur_page))
    c.setTitle(f"{MOIS[mois - 1]} {annee}")
    c.setAuthor("Planning du matériel topo")
    Y = lambda t: hauteur_page - t  # noqa: E731  (coordonnées « depuis le haut »)

    x_code = X_TABLE + L_CAT
    x_num = x_code + L_CODE
    x_jours = x_num + L_NUM
    n = d["n"]
    l_jour = (X_FIN - x_jours) / n
    xj = lambda j: x_jours + (j - 1) * l_jour  # noqa: E731

    def trait(x1, t1, x2, t2, epaisseur, couleur=black):
        c.setStrokeColor(couleur)
        c.setLineWidth(epaisseur)
        c.line(x1, Y(t1), x2, Y(t2))

    def rect(x, t, w, h, fond):
        c.setFillColor(HexColor(fond))
        c.rect(x, Y(t + h), w, h, stroke=0, fill=1)

    def texte_vertical(x, t_bas, texte, police, taille):
        c.saveState()
        c.translate(x, Y(t_bas))
        c.rotate(90)
        c.setFillColor(black)
        c.setFont(police, taille)
        c.drawString(0, 0, texte)
        c.restoreState()

    # ---- Hauteurs des lignes : chaque catégorie a au moins MIN_LIGNES_GROUPE unités.
    unites = [max(len(g["articles"]), MIN_LIGNES_GROUPE) for g in d["groupes"]] or [1]
    h_unite = (T_FIN - T_LIGNES) / sum(unites)

    # ---- En-tête
    c.setFillColor(black)
    c.setFont(POLICE_GRAS, 6.8)
    c.drawCentredString((x_jours + X_FIN) / 2, Y(T_DATES - 2.3), MOIS[mois - 1])
    rect(x_code, T_CODE_TETE, L_CODE, T_LIGNES - T_CODE_TETE, GRIS_CODE)
    for i, morceau in enumerate(["N°  MS  -", "A facturer"]):
        texte_vertical(x_code + 13.5 + i * 10, T_LIGNES - 3, morceau, POLICE, 7.8)
    for j in range(1, n + 1):
        jour = dt.date(annee, mois, j)
        xc = xj(j) + l_jour / 2 + 2
        texte_vertical(xc, T_LIGNES - 34.4, jour.strftime("%d.%m.%Y"), POLICE, 5.4)
        texte_vertical(xc, T_LIGNES - 1.5, JOURS[jour.weekday()], POLICE, 5.4)

    # ---- Séparations des jours (dessinées en premier : les barres passent par-dessus)
    for j in range(2, n + 1):
        trait(xj(j), T_DATES, xj(j), T_FIN, TRAIT_FIN, Color(0.25, 0.25, 0.25))

    # ---- Lignes des articles
    par_article = {}
    for af in d["affectations"]:
        par_article.setdefault(af["article_id"], []).append(af)
    t = T_LIGNES
    limites_groupes = [T_LIGNES]
    for g, u in zip(d["groupes"], unites):
        h_ligne = h_unite * u / len(g["articles"])
        t_groupe = t
        for a in g["articles"]:
            rect(x_code, t, L_CODE, h_ligne, GRIS_CODE)
            rect(x_num, t, L_NUM, h_ligne, a["couleur"])
            c.setFillColor(black)
            c.setFont(POLICE, 7.8)
            c.drawCentredString(x_code + L_CODE / 2, Y(t + h_ligne / 2 + 2.6), couper_texte(a["code_compta"], POLICE, 7.8, L_CODE - 3))
            taille_num = 7.3
            while taille_num > 5.5 and pdfmetrics.stringWidth(a["numero_interne"], POLICE, taille_num) > L_NUM - 3:
                taille_num -= 0.25
            c.setFont(POLICE, taille_num)
            c.drawString(x_num + 1.5, Y(t + h_ligne / 2 + taille_num / 3),
                         couper_texte(a["numero_interne"], POLICE, taille_num, L_NUM - 3))
            # Barres d'affectation
            for af in par_article.get(a["id"], []):
                x1, x2 = xj(af["j1"]), xj(af["j2"] + 1)
                rect(x1, t, x2 - x1, h_ligne, a["couleur"])
                c.setStrokeColor(black)
                c.setLineWidth(TRAIT_MOYEN)
                c.rect(x1, Y(t + h_ligne), x2 - x1, h_ligne, stroke=1, fill=0)
                taille = 5.2 if h_ligne >= 10 else 4.6
                c.setFillColor(black)
                c.setFont(POLICE, taille)
                c.drawCentredString((x1 + x2) / 2, Y(t + h_ligne / 2 + taille * 0.35),
                                    couper_texte(af["libelle"], POLICE, taille, x2 - x1 - 3))
            t += h_ligne
            if t < t_groupe + h_unite * u - 0.1:
                trait(x_code, t, X_FIN, t, TRAIT_MOYEN)
        # Nom de la catégorie : vertical, sur plusieurs lignes si besoin ; horizontal si la catégorie est basse.
        h_groupe = t - t_groupe
        taille = 7.8
        if pdfmetrics.stringWidth(g["nom"], POLICE_GRAS, taille) > h_groupe - 6 and \
                pdfmetrics.stringWidth(g["nom"], POLICE_GRAS, taille) <= L_CAT - 6:
            c.setFillColor(black)
            c.setFont(POLICE_GRAS, taille)
            c.drawCentredString(X_TABLE + L_CAT / 2, Y(t_groupe + h_groupe / 2 + 2.6), g["nom"])
        else:
            lignes = lignes_mots(g["nom"], POLICE_GRAS, taille, h_groupe - 6)
            while len(lignes) * (taille + 1) > L_CAT - 4 and taille > 5:
                taille -= 0.5
                lignes = lignes_mots(g["nom"], POLICE_GRAS, taille, h_groupe - 6)
            bloc = len(lignes) * (taille + 1)
            for i, ligne in enumerate(lignes):
                x = X_TABLE + L_CAT / 2 - bloc / 2 + (i + 1) * (taille + 1) - 2
                w = pdfmetrics.stringWidth(ligne, POLICE_GRAS, taille)
                texte_vertical(x, t_groupe + h_groupe / 2 + w / 2, ligne, POLICE_GRAS, taille)
        limites_groupes.append(t)

    # ---- Grille
    for tg in limites_groupes:  # séparations des catégories
        trait(X_TABLE, tg, X_FIN, tg, TRAIT_FORT)
    trait(x_jours, T_DATES, X_FIN, T_DATES, TRAIT_FORT)
    trait(x_code, T_CODE_TETE, x_num, T_CODE_TETE, TRAIT_FORT)
    trait(x_code, T_CODE_TETE, x_code, T_FIN, TRAIT_MOYEN)
    trait(x_num, T_CODE_TETE, x_num, T_FIN, TRAIT_MOYEN)
    trait(x_code, T_LIGNES, x_code, T_FIN, TRAIT_MOYEN)
    trait(x_jours, T_TABLE, x_jours, T_FIN, TRAIT_FORT)
    c.setStrokeColor(black)
    c.setLineWidth(TRAIT_FORT)
    c.rect(X_TABLE, Y(T_FIN), X_FIN - X_TABLE, T_FIN - T_TABLE, stroke=1, fill=0)

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
