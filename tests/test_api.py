"""Tests automatiques du serveur. Lancement : python -m unittest discover tests"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

DOSSIER_TEST = tempfile.mkdtemp(prefix="planning-test-")
os.environ["PLANNING_DONNEES"] = DOSSIER_TEST
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import base  # noqa: E402
from api import creer_app  # noqa: E402


class TestApi(unittest.TestCase):
    def setUp(self):
        if base.FICHIER_BASE.exists():
            base.FICHIER_BASE.unlink()
        base.initialiser()
        self.c = creer_app().test_client()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)

    def categorie(self, nom="Canne GPS"):
        return self.c.post("/api/categories", json={"nom": nom}).get_json()["id"]

    def article(self, cat, numero="953", **autres):
        d = {"categorie_id": cat, "numero_interne": numero, "couleur": "#F2CEEF", **autres}
        return self.c.post("/api/articles", json=d)

    def test_categories_ordre_et_doublon(self):
        a, b = self.categorie("A"), self.categorie("B")
        self.assertEqual(self.c.post("/api/categories", json={"nom": "a"}).status_code, 400)
        self.c.post(f"/api/categories/{b}/deplacer", json={"sens": -1})
        noms = [x["nom"] for x in self.c.get("/api/categories").get_json()]
        self.assertEqual(noms, ["B", "A"])

    def test_article_creation_modification(self):
        cat = self.categorie()
        r = self.article(cat, code_compta="112", prix_chf="1'250.50", date_achat="2024-03-15")
        self.assertEqual(r.status_code, 201, r.get_json())
        ident = r.get_json()["id"]
        a = self.c.get(f"/api/articles/{ident}").get_json()
        self.assertEqual(a["prix_chf"], 1250.5)
        self.assertEqual(a["code_compta"], "112")
        self.assertIsNone(a["aujourdhui"])
        # Le code compta peut se répéter, le n° interne non.
        self.assertEqual(self.article(cat, "9531", code_compta="112").status_code, 201)
        self.assertEqual(self.article(cat, "953").status_code, 400)
        d = {**a, "statut": "reparation", "numero_interne": "953 bis"}
        self.assertEqual(self.c.put(f"/api/articles/{ident}", json=d).status_code, 200)
        self.assertEqual(self.c.get(f"/api/articles/{ident}").get_json()["statut"], "reparation")

    def test_validations(self):
        cat = self.categorie()
        self.assertEqual(self.article(cat, "").status_code, 400)
        self.assertEqual(self.article(cat, "X", couleur="rouge").status_code, 400)
        self.assertEqual(self.article(cat, "X", date_achat="31.02.2024").status_code, 400)
        self.assertEqual(self.article(cat, "X", prix_chf="abc").status_code, 400)

    def test_ordre_articles(self):
        cat = self.categorie()
        ids = [self.article(cat, n).get_json()["id"] for n in ("A", "B", "C")]
        self.c.post(f"/api/articles/{ids[2]}/deplacer", json={"sens": -1})
        self.assertEqual([a["numero_interne"] for a in self.c.get("/api/articles").get_json()], ["A", "C", "B"])

    def test_photo_et_documents(self):
        ident = self.article(self.categorie()).get_json()["id"]
        r = self.c.post(f"/api/articles/{ident}/photo", data={"fichier": (io.BytesIO(b"img"), "p.jpg")},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200)
        photo = r.get_json()["photo"]
        self.assertTrue((base.DOSSIER_FICHIERS / "photos" / photo).exists())
        r = self.c.post(f"/api/articles/{ident}/documents",
                        data={"fichiers": [(io.BytesIO(b"pdf"), "Notice GS18.pdf"), (io.BytesIO(b"x"), "facture.pdf")]},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 201)
        docs = self.c.get(f"/api/articles/{ident}").get_json()["documents"]
        self.assertEqual([d["nom_original"] for d in docs], ["Notice GS18.pdf", "facture.pdf"])
        self.assertEqual(self.c.get(f"/api/documents/{docs[0]['id']}").data, b"pdf")
        self.assertEqual(self.c.delete(f"/api/articles/{ident}").status_code, 200)
        self.assertFalse((base.DOSSIER_FICHIERS / "photos" / photo).exists())

    def test_chantiers(self):
        r = self.c.post("/api/chantiers", json={"numero": "855325", "nom": "Begnins", "responsable": "Junior"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["numero"], "855 325")
        self.assertTrue(r.get_json()["facturable"])
        # Même numéro écrit autrement : refusé.
        self.assertEqual(self.c.post("/api/chantiers", json={"numero": "855 325", "nom": "X"}).status_code, 400)
        # Sans numéro : unicité sur le nom.
        self.assertEqual(self.c.post("/api/chantiers", json={"nom": "RONCHI"}).status_code, 201)
        self.assertEqual(self.c.post("/api/chantiers", json={"nom": "ronchi"}).status_code, 400)

    def test_suppression_protegee_par_historique(self):
        cat = self.categorie()
        art = self.article(cat).get_json()["id"]
        ch = self.c.post("/api/chantiers", json={"numero": "10203", "nom": "OFROU"}).get_json()["id"]
        con = base.connecter()
        con.execute("INSERT INTO affectation (article_id, chantier_id, date_debut, date_fin) VALUES (?, ?, '2026-01-01', '2099-12-31')",
                    (art, ch))
        con.commit()
        con.close()
        self.assertEqual(self.c.delete(f"/api/articles/{art}").status_code, 409)
        self.assertEqual(self.c.delete(f"/api/chantiers/{ch}").status_code, 409)
        self.assertEqual(self.c.delete(f"/api/categories/{cat}").status_code, 409)
        a = self.c.get(f"/api/articles/{art}").get_json()
        self.assertEqual(a["aujourdhui"]["chantier_numero"], "10 203")
        self.assertEqual(len(a["historique"]), 1)


def excel_fictif():
    """Petit classeur au format de l'ancien planning (données inventées)."""
    import openpyxl
    from openpyxl.styles import PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A4"] = "Canne GPS"
    ws.merge_cells("A4:A6")
    for r, (code, num, coul) in enumerate([(112, "G1", "FFB7B7"), (None, "G2", "FFFFB9"), (103, "G3", "CCE0F4")], start=4):
        ws.cell(r, 2, code)
        ws.cell(r, 3, num).fill = PatternFill("solid", fgColor=coul)
    ws["A7"] = "GUIDAGE"
    ws.merge_cells("A7:A8")
    ws["D4"] = "111 222 Ville A - Dupont"
    ws.merge_cells("D4:J4")
    ws["K4"] = "111 222 Ville A - Dupont"
    ws.merge_cells("K4:M4")
    ws["D5"] = "333444 Ville B Martin"
    ws.merge_cells("D5:E5")
    ws["F6"] = "INTERNE"
    ws.merge_cells("F6:H6")
    ws["G5"] = "10555"
    flux = io.BytesIO()
    wb.save(flux)
    flux.seek(0)
    return flux


class TestPreremplissage(TestApi):
    # Hérite de setUp ; les tests de TestApi ne sont pas relancés ici.
    test_categories_ordre_et_doublon = test_article_creation_modification = test_validations = None
    test_ordre_articles = test_photo_et_documents = test_chantiers = test_suppression_protegee_par_historique = None
    def test_analyse_et_creation(self):
        r = self.c.post("/api/preremplissage/analyse", data={"fichier": (excel_fictif(), "planning.xlsx")},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 200, r.get_json())
        d = r.get_json()
        self.assertEqual(d["categories"], ["Canne GPS", "GUIDAGE"])
        self.assertEqual([a["numero_interne"] for a in d["articles"]], ["G1", "G2", "G3", "Guidage 1", "Guidage 2"])
        self.assertEqual(d["articles"][0]["couleur"], "#FFB7B7")
        self.assertEqual(d["articles"][1]["code_compta"], "")
        ch = {c["numero"]: c for c in d["chantiers"]}
        self.assertEqual(ch["111 222"]["nom"], "Ville A")       # responsable retiré
        self.assertFalse(ch["111 222"]["a_verifier"])
        self.assertTrue(ch["333 444"]["a_verifier"])            # pas de tiret : à vérifier
        self.assertTrue(ch["10 555"]["a_verifier"])
        self.assertEqual(ch[""]["nom"], "INTERNE")
        # Un chantier sans nom est refusé : l'utilisateur doit le compléter.
        r = self.c.post("/api/preremplissage/valider", json={"articles": [], "chantiers": [ch["10 555"]]})
        self.assertEqual(r.status_code, 400)
        ch["10 555"]["nom"] = "Ville C"
        r = self.c.post("/api/preremplissage/valider", json={"articles": d["articles"], "chantiers": d["chantiers"]})
        self.assertEqual(r.get_json(), {"categories": 2, "articles": 5, "chantiers": 4, "ignores": 0})
        # Deuxième passage : tout existe déjà, rien n'est dupliqué.
        r = self.c.post("/api/preremplissage/valider", json={"articles": d["articles"], "chantiers": d["chantiers"]})
        self.assertEqual(r.get_json()["ignores"], 9)
        self.assertEqual(len(self.c.get("/api/articles").get_json()), 5)

    def test_mauvais_fichier(self):
        r = self.c.post("/api/preremplissage/analyse", data={"fichier": (io.BytesIO(b"pas un excel"), "x.xlsx")},
                        content_type="multipart/form-data")
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
