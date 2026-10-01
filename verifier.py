"""Verification de l'environnement, a lancer avant chaque TP.

    python verifier.py

Trente secondes qui evitent de decouvrir un probleme a la vingtieme minute
d'un TP, sur une machine parmi trente, devant une salle qui attend.

Ce qui est verifie
------------------
    la version de Python
    l'environnement virtuel est bien actif
    les paquets de requirements.txt sont installes
    .env existe, et n'est pas suivi par git
    deux fournisseurs sont configures, plus celui des mesures
    un appel de test reussit chez chacun
    les reponses hors ligne sont disponibles
    le miroir de paquets de la salle repond, s'il est annonce
"""

from __future__ import annotations

import importlib.metadata
import os
import re
import subprocess
import sys
from pathlib import Path

VERT, ROUGE, JAUNE, GRIS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[0m"
if os.name == "nt" and not os.environ.get("WT_SESSION"):
    VERT = ROUGE = JAUNE = GRIS = FIN = ""     # console Windows sans couleurs

PYTHON_MINIMAL = (3, 10)      # mcp (TP4), langgraph (TP8), fastapi (TP3)
PYTHON_MIROIR = {(3, 13), (3, 14)}   # les versions servies par le miroir de la salle
MIROIR_SALLE = "http://192.168.8.2:8000"

problemes: list[str] = []


def ok(texte: str) -> None:
    print(f"  {VERT}ok{FIN}     {texte}")


def echec(texte: str, remede: str) -> None:
    print(f"  {ROUGE}ECHEC{FIN}  {texte}")
    print(f"         {GRIS}{remede}{FIN}")
    problemes.append(texte)


def alerte(texte: str, remede: str = "") -> None:
    print(f"  {JAUNE}note{FIN}   {texte}")
    if remede:
        print(f"         {GRIS}{remede}{FIN}")


# --------------------------------------------------------------------------

def verifier_python() -> None:
    v = sys.version_info
    if v[:2] < PYTHON_MINIMAL:
        echec(f"Python {v.major}.{v.minor}, il en faut "
              f"{PYTHON_MINIMAL[0]}.{PYTHON_MINIMAL[1]} ou plus",
              "Installez Python 3.13 ou 3.14, puis recreez l'environnement.")
        return
    ok(f"Python {v.major}.{v.minor}.{v.micro}")
    if v[:2] not in PYTHON_MIROIR:
        alerte(f"Python {v.major}.{v.minor} : le miroir hors ligne de la salle "
               f"ne porte que les paquets de Python 3.13 et 3.14",
               "Hors de la salle, tout fonctionne. En salle, sans internet, "
               "pip ne trouvera pas vos paquets.")


def verifier_venv() -> None:
    actif = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if actif:
        ok(f"environnement virtuel actif ({Path(sys.prefix).name})")
    else:
        echec("environnement virtuel non actif",
              "Windows : .venv\\Scripts\\activate   "
              "macOS, Linux : source .venv/bin/activate")


def nom_distribution(ligne: str) -> str:
    """Le nom du paquet, sans version, extras ni marqueur.

    requests~=2.31, requests<3, uvicorn[standard]>=0.30, mcp ; python_version...
    """
    ligne = ligne.split("#")[0].strip()
    if not ligne or ligne.startswith("-"):
        return ""
    return re.split(r"[<>=!~;\[\s@]", ligne, maxsplit=1)[0].strip()


def verifier_paquets() -> None:
    fichier = Path("requirements.txt")
    if not fichier.exists():
        alerte("requirements.txt introuvable",
               "Lancez la commande depuis la racine du depot.")
        return
    manquants = []
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        nom = nom_distribution(ligne)
        if not nom:
            continue
        # On interroge les paquets installes, pas les modules importables :
        # opentelemetry-sdk s'importe sous opentelemetry.sdk, arize-phoenix
        # sous phoenix. Chercher le module par son nom de paquet se trompe.
        try:
            importlib.metadata.version(nom)
        except importlib.metadata.PackageNotFoundError:
            manquants.append(nom)
    if manquants:
        echec(f"paquets absents : {', '.join(manquants)}",
              f"En salle : pip install --no-index --trusted-host "
              f"{MIROIR_SALLE.split('//')[1].split(':')[0]} "
              f"--find-links={MIROIR_SALLE}/roue -r requirements.txt")
    else:
        ok("tous les paquets de requirements.txt sont installes")


def verifier_env() -> None:
    if not Path(".env").exists():
        echec(".env introuvable",
              "cp .env.exemple .env, puis renseignez vos cles.")
        return
    ok(".env present")

    try:
        suivi = subprocess.run(["git", "ls-files", "--error-unmatch", ".env"],
                               capture_output=True, text=True, timeout=10)
        if suivi.returncode == 0:
            echec(".env EST SUIVI PAR GIT",
                  "git rm --cached .env, puis verifiez .gitignore. "
                  "Puis changez la cle chez le fournisseur : une cle poussee "
                  "sur GitHub doit etre consideree comme publiee.")
        else:
            ok(".env n'est pas suivi par git")
    except (OSError, subprocess.SubprocessError):
        alerte("git indisponible, impossible de verifier le suivi de .env")


def verifier_fournisseurs() -> None:
    try:
        from client_llm import Client, ErreurFournisseur, charger_env
    except ImportError:
        echec("client_llm.py introuvable",
              "Lancez la commande depuis la racine du depot.")
        return

    charger_env()
    principal = os.environ.get("FOURNISSEUR_PRINCIPAL")
    secours = os.environ.get("FOURNISSEUR_SECOURS")
    mesure = os.environ.get("FOURNISSEUR_MESURE")

    if not principal:
        echec("aucun fournisseur configure",
              "Renseignez FOURNISSEUR_PRINCIPAL dans .env.")
        return
    if not secours:
        echec("aucun fournisseur de secours",
              "Le module en demande deux : une offre gratuite peut fermer ou "
              "changer en cours de semestre. Ajoutez FOURNISSEUR_SECOURS.")
    if not mesure:
        echec("aucun fournisseur de mesure",
              "Ajoutez FOURNISSEUR_MESURE : un fournisseur sans quota "
              "journalier annonce, ou mesure.py epuisera votre principal "
              "(annexe C, §7).")

    # Le secours doit servir le meme modele que le principal : une bascule au
    # milieu d'une execution ne doit pas changer le comportement de l'agent.
    if principal and secours:
        def modele(nom: str) -> str:
            return os.environ.get(
                f"LLM_{nom.upper().replace('-', '_')}_MODELE", "").split("/")[-1]
        if modele(principal) and modele(secours) \
                and modele(principal) != modele(secours):
            alerte(f"le secours ({secours}) ne sert pas le meme modele que le "
                   f"principal ({principal})",
                   "Une bascule changera le comportement de l'agent au milieu "
                   "d'une execution. L'annexe C, §7, donne un secours qui sert "
                   "le meme modele.")
    # Le fournisseur de grande fenetre, appele par son nom au TP2 et pour le
    # moteur A du TP1 bis. Il n'est pas exige avant le bloc 1.5.
    fenetre = os.environ.get("FOURNISSEUR_GRANDE_FENETRE")
    if not fenetre:
        alerte("aucun FOURNISSEUR_GRANDE_FENETRE dans .env",
               "Le TP2 et le moteur A du TP1 bis en ont besoin (annexe C, §7). "
               "Ajoutez-le avant le bloc 1.5.")

    noms = []
    for nom in (principal, secours, mesure, fenetre):
        if nom and nom not in noms:
            noms.append(nom)

    for nom in noms:
        variable = f"LLM_{nom.upper().replace('-', '_')}_CLE"
        if os.environ.get(variable, "").strip() in ("", "..."):
            remede = (f"Collez votre cle dans .env, a la ligne {variable}=, a la place "
                      f"des trois points. Le compte se cree en suivant l'annexe C, §7.")
            # La grande fenetre ne sert qu'a partir du bloc 1.5 : elle previent
            # sans bloquer.
            if nom == fenetre and nom not in (principal, secours, mesure):
                alerte(f"{nom} : pas encore de cle, il en faut une avant le bloc 1.5", remede)
            else:
                echec(f"{nom} : pas de cle", remede)
            continue
        try:
            client = Client(fournisseur=nom, journal=None)
            reponse = client.appeler(
                [{"role": "user", "content": "Reponds exactement : pret"}])
            ok(f"{nom} repond  ({reponse.tokens_entree} tokens en entree, "
               f"{reponse.cout:.6f} $)")
            if reponse.cout == 0.0:
                alerte(f"{nom} : prix non renseignes dans .env",
                       f"Sans LLM_{nom.upper().replace('-', '_')}_PRIX_ENTREE et "
                       f"LLM_{nom.upper().replace('-', '_')}_PRIX_SORTIE, mesure.py rendra "
                       "un cout de zero, et le bloc 11 sera impossible.")
        except ErreurFournisseur as erreur:
            echec(f"{nom} : {erreur}", "Verifiez la cle et l'URL dans .env.")
        except Exception as erreur:                          # noqa: BLE001
            texte = str(erreur)
            # Une cle refusee n'est pas une panne de reseau : le remede differe.
            if any(code in texte for code in ("401", "403", "400 ")):
                remede = (f"La cle est refusee. Recopiez-la dans .env, a la ligne "
                          f"{variable}=, sans espace. Reessayer sans la changer ne sert a rien.")
            else:
                remede = "Etes-vous sur le reseau MD26 ? Sinon, le fournisseur est peut-etre en panne."
            echec(f"{nom} : {type(erreur).__name__} {texte[:200]}", remede)


def verifier_hors_ligne() -> None:
    try:
        from hors_ligne import Rejeu
    except ImportError:
        return
    rejeu = Rejeu()
    if len(rejeu) > 0:
        ok(f"{len(rejeu)} reponses hors ligne disponibles")
    else:
        alerte("aucune reponse hors ligne capturee",
               "Sans elles, une panne de reseau arrete le TP.")


def verifier_miroir() -> None:
    try:
        import requests
        requests.get(MIROIR_SALLE, timeout=2)
        ok(f"miroir de la salle joignable ({MIROIR_SALLE})")
    except Exception:                                        # noqa: BLE001
        alerte(f"miroir de la salle injoignable ({MIROIR_SALLE})",
               "Normal hors de la salle. En salle : etes-vous sur MD26 ?")


# --------------------------------------------------------------------------

def main() -> int:
    print("\n  Verification de l'environnement MD-26\n")
    verifier_python()
    verifier_venv()
    verifier_paquets()
    verifier_env()
    print()
    verifier_fournisseurs()
    verifier_hors_ligne()
    verifier_miroir()
    print()

    if problemes:
        print(f"  {ROUGE}{len(problemes)} probleme(s) a regler avant le TP.{FIN}\n")
        return 1
    print(f"  {VERT}Tout est pret.{FIN}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
