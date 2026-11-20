"""Point d'entrée : démarre l'application et ouvre le navigateur.

Lancement : double-clic sur « Lancer.bat » (Windows), ou « python app/serveur.py ».
"""
import json
import socket
import sys
import threading
import urllib.request
import webbrowser

import base
from api import IDENTITE, creer_app

# Ports essayés dans l'ordre. Si un port est déjà pris par un autre logiciel,
# on passe au suivant : l'application ne se confond jamais avec une autre.
PORTS = range(47310, 47330)


def port_occupe(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def est_notre_application(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/identite", timeout=1) as r:
            return json.load(r).get("application") == IDENTITE
    except Exception:
        return False


def choisir_port():
    """Renvoie (port, deja_lance)."""
    for port in PORTS:
        if not port_occupe(port):
            return port, False
        if est_notre_application(port):
            return port, True
    raise SystemExit("Aucun port libre trouvé (47310 à 47329). Fermez d'autres logiciels puis relancez.")


def main():
    ouvrir = "--sans-navigateur" not in sys.argv
    port, deja_lance = choisir_port()
    adresse = f"http://localhost:{port}"
    if deja_lance:
        print(f"L'application est déjà lancée ({adresse}) : ouverture du navigateur.")
        if ouvrir:
            webbrowser.open(adresse)
        return

    base.initialiser()
    app = creer_app()

    print("=" * 60)
    print("  Planning du matériel topo")
    print(f"  Adresse : {adresse}")
    print(f"  Données : {base.DOSSIER_DONNEES}")
    print()
    print("  Laissez cette fenêtre ouverte pendant l'utilisation.")
    print("  Pour arrêter l'application : fermez cette fenêtre.")
    print("=" * 60)

    if ouvrir:
        threading.Timer(1.0, lambda: webbrowser.open(adresse)).start()

    from waitress import serve
    # 127.0.0.1 : l'application n'est accessible que depuis ce PC.
    serve(app, host="127.0.0.1", port=port, threads=4, _quiet=True)


if __name__ == "__main__":
    main()
