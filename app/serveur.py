"""Point d'entrée : démarre l'application et ouvre le navigateur.

Lancement : double-clic sur « Lancer.bat » (Windows), ou « python app/serveur.py ».
"""
import socket
import sys
import threading
import webbrowser

import base
from api import creer_app

PORT = 8765
ADRESSE = f"http://localhost:{PORT}"


def deja_lance():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def main():
    ouvrir = "--sans-navigateur" not in sys.argv
    if deja_lance():
        print("L'application est déjà lancée : ouverture du navigateur.")
        if ouvrir:
            webbrowser.open(ADRESSE)
        return

    base.initialiser()
    app = creer_app()

    print("=" * 60)
    print("  Planning du matériel topo")
    print(f"  Adresse : {ADRESSE}")
    print(f"  Données : {base.DOSSIER_DONNEES}")
    print()
    print("  Laissez cette fenêtre ouverte pendant l'utilisation.")
    print("  Pour arrêter l'application : fermez cette fenêtre.")
    print("=" * 60)

    if ouvrir:
        threading.Timer(1.0, lambda: webbrowser.open(ADRESSE)).start()

    from waitress import serve
    # 127.0.0.1 : l'application n'est accessible que depuis ce PC.
    serve(app, host="127.0.0.1", port=PORT, threads=4, _quiet=True)


if __name__ == "__main__":
    main()
