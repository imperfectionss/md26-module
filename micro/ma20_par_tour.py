# -*- coding: utf-8 -*-
"""MA-20 · L'ablation minute (bloc 3).

La meme tache avec 3, 6 et 12 outils, une fois chacune : ce qui se compare,
ce sont les tokens par tour. Ce script lit les trois mesures et fait le
calcul, sans aucun appel.

D'abord, depuis la racine de votre copie du depot, apres l'etape 1 du TP3
(vos six definitions) :

    python mesure.py --agent sanad --taches taches/b3.jsonl --limite 1 --repetitions 1 --outils 3 --sortie mesures/ma20_3.json
    python mesure.py --agent sanad --taches taches/b3.jsonl --limite 1 --repetitions 1 --outils 6 --sortie mesures/ma20_6.json
    python mesure.py --agent sanad --taches taches/b3.jsonl --limite 1 --repetitions 1 --outils 12 --sortie mesures/ma20_12.json

puis :

    python micro/ma20_par_tour.py

Les tokens par tour : la somme des tokens envoyes, divisee par la somme des
tours, sur les executions du fichier. C'est le calcul du chapitre 6, §6.5.2.
Sortie, dans observations/b3.md : trois nombres et le nombre d'outils que
vous recommandez. Trois executions ne donnent pas de taux : les tokens, si.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FICHIERS = ["mesures/ma20_3.json", "mesures/ma20_6.json", "mesures/ma20_12.json"]


def par_tour(fichier: Path) -> tuple[int, int, int]:
    """(outils, tokens envoyes, tours), lus dans une mesure de mesure.py."""
    d = json.loads(fichier.read_text(encoding="utf-8"))
    essais = d.get("essais") or []
    outils = (d.get("options") or {}).get("outils")
    return outils, sum(int(e.get("tokens_entree") or 0) for e in essais), sum(int(e.get("tours") or 0) for e in essais)


def main(arguments: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print()
    for nom in arguments or FICHIERS:
        f = Path(nom)
        if not f.exists():
            print(f"  {nom} manque : lancez d'abord la mesure correspondante (voir l'en-tete du script).")
            continue
        try:
            outils, tokens, tours = par_tour(f)
        except (ValueError, OSError) as e:
            print(f"  {nom} : fichier illisible ({e}).")
            continue
        if not tours:
            print(f"  {nom} : aucun tour enregistre, la mesure n'a rien fait tourner.")
            continue
        print(f"  {str(outils or '?'):>3} outils   {tokens:>7} tokens envoyes   {tours:>3} tours"
              f"   {round(tokens / tours):>6} tokens par tour")
    print("\n  A noter dans observations/b3.md : les trois nombres, et le nombre d'outils que vous recommandez.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
