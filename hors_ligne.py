"""Capture et rejeu des reponses de modele, pour travailler sans reseau.

Le reseau de la salle n'est pas celui de l'etablissement, les quotas gratuits
s'epuisent, et une offre gratuite peut fermer ou changer en cours de semestre.
Chaque TP qui appelle une API a donc un mode hors ligne.

    python mesure.py ... --capturer          avec une cle et du reseau
    python mesure.py ... --hors-ligne        sans rien

La meme chose sans mesure.py : MD26_CAPTURER=hors_ligne/moi ou
MD26_HORS_LIGNE=1 dans l'environnement, ou Client(capturer=...) et
Client(hors_ligne=True) dans le code.

La regle, et elle n'est pas negociable
--------------------------------------
Une sortie enregistree se CAPTURE, elle ne s'invente pas. Une sortie fabriquee
ne correspondra pas a ce que la salle voit tourner, et la classe le remarque en
trente secondes.

Ce que le rejeu sait faire, et ce qu'il ne sait pas faire
---------------------------------------------------------
La cle est une empreinte du contenu envoye : les messages, les definitions
d'outils, le fournisseur et le modele. Deux appels identiques rejouent la meme
reponse. Un appel jamais capture leve RejeuIntrouvable plutot que d'inventer.

Consequences, a connaitre avant de compter sur le rejeu :

- un prompt ou une description d'outil modifies depuis la capture ne sont
  plus reconnus : recapturez ;
- une question nouvelle, une attaque nouvelle, n'ont pas de reponse ;
- les k executions d'une meme tache rejouent la meme reponse : en rejeu, le
  taux de resolution et la reussite repetee sont egaux par construction ;
- les latences rejouees valent zero.

Quand aucune capture n'existe pour le modele demande, le rejeu accepte une
capture des memes messages faite avec un autre modele, et le dit, sauf en
mode strict (Client(fournisseur=...) avec un nom explicite, le TP1 bis).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


DOSSIER_DEFAUT = Path("hors_ligne")


class RejeuIntrouvable(KeyError):
    """Cet appel n'a jamais ete capture. On ne fabrique pas de reponse."""


def empreinte(messages: list[dict], outils: list[dict] | None = None,
              fournisseur: str = "", modele: str = "") -> str:
    """Empreinte stable d'un appel.

    Les cles sont triees : un ordre de dictionnaire qui varie produirait une
    empreinte differente pour le meme appel. C'est la meme discipline que
    celle qui fait fonctionner le cache de prefixe du bloc 2.

    Sans fournisseur ni modele, l'empreinte ne porte que sur le contenu :
    c'est celle qui sert au rejeu non strict.
    """
    charge = {"messages": messages, "outils": outils or []}
    if fournisseur or modele:
        charge["fournisseur"] = fournisseur
        charge["modele"] = modele
    texte = json.dumps(charge, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()[:16]


class Rejeu:
    """Lit les reponses capturees et les rend a l'identique."""

    def __init__(self, dossier: Path | None = None) -> None:
        self.dossier = Path(dossier or DOSSIER_DEFAUT)
        self._exact: dict[str, dict] = {}
        self._contenu: dict[str, dict] = {}
        self._modeles: dict[str, str] = {}
        self._deja_signale: set[str] = set()
        self._charger()

    def _charger(self) -> None:
        if not self.dossier.exists():
            return
        for fichier in sorted(self.dossier.rglob("*.jsonl")):
            for ligne in fichier.read_text(encoding="utf-8").splitlines():
                ligne = ligne.strip()
                if not ligne:
                    continue
                entree = json.loads(ligne)
                reponse = entree["reponse"]
                self._exact[entree["empreinte"]] = reponse
                # Les captures anterieures au 25 septembre 2026 n'ont que
                # l'empreinte du contenu.
                contenu = entree.get("empreinte_contenu", entree["empreinte"])
                self._contenu.setdefault(contenu, reponse)
                self._modeles.setdefault(
                    contenu, f"{entree.get('fournisseur', '?')}/"
                             f"{entree.get('modele', '?')}")

    def chercher(self, messages: list[dict], outils: list[dict] | None = None,
                 fournisseur: str = "", modele: str = "",
                 strict: bool = False) -> dict:
        exacte = empreinte(messages, outils, fournisseur, modele)
        if exacte in self._exact:
            return self._exact[exacte]

        contenu = empreinte(messages, outils)
        if not strict and contenu in self._contenu:
            capture = self._modeles.get(contenu, "?")
            demande = f"{fournisseur or '?'}/{modele or '?'}"
            if (fournisseur or modele) and capture not in self._deja_signale:
                print(f"  rejeu : reponse capturee avec {capture}, "
                      f"pas avec {demande}.")
                self._deja_signale.add(capture)
            return self._contenu[contenu]

        raise RejeuIntrouvable(
            f"Appel non capture (empreinte {exacte}).\n"
            f"  {len(self)} reponses disponibles dans {self.dossier}/.\n"
            f"  Le rejeu ne connait que les appels deja faits : un prompt ou "
            f"une description d'outil modifies, une question nouvelle, n'y "
            f"sont pas.\n"
            f"  Capturez vos propres appels avec --capturer, tant que vous "
            f"avez du reseau.")

    def __len__(self) -> int:
        return len(self._exact)


class Capture:
    """Enregistre les reponses reelles, pour les rejouer plus tard.

    Client(capturer=Path("hors_ligne/moi")) le fait a chaque reponse 200.
    Les captures ne contiennent ni cle ni en-tete : elles se commitent, et
    c'est ce qui permet a l'integration continue de rejouer vos mesures.
    """

    def __init__(self, dossier: Path) -> None:
        self.dossier = Path(dossier)
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.fichier = self.dossier / "reponses.jsonl"
        self.vues: set[str] = set()
        if self.fichier.exists():
            for ligne in self.fichier.read_text(encoding="utf-8").splitlines():
                if ligne.strip():
                    self.vues.add(json.loads(ligne)["empreinte"])

    def ajouter(self, messages: list[dict], outils: list[dict] | None,
                reponse_brute: dict, fournisseur: str = "",
                modele: str = "") -> bool:
        """Rend True si l'appel etait nouveau."""
        cle = empreinte(messages, outils, fournisseur, modele)
        if cle in self.vues:
            return False
        with self.fichier.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "empreinte": cle,
                "empreinte_contenu": empreinte(messages, outils),
                "fournisseur": fournisseur,
                "modele": modele,
                "reponse": reponse_brute,
            }, ensure_ascii=False) + "\n")
        self.vues.add(cle)
        return True

    def __len__(self) -> int:
        return len(self.vues)


if __name__ == "__main__":
    import sys
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else DOSSIER_DEFAUT
    rejeu = Rejeu(dossier)
    print(f"{len(rejeu)} reponses capturees dans {dossier}/")
    if len(rejeu) == 0:
        print("Aucune capture. Lancez une mesure avec --capturer, "
              "avec une cle et du reseau.")
