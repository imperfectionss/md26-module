# -*- coding: utf-8 -*-
"""MA-15 · L'aiguille, trois fois (bloc 2).

Le meme fait, au debut, au milieu et a la fin d'un contexte de 20 000 tokens,
deux essais par position. Le fait est celui du chapitre 5, §5.1 : le delai de
regularisation d'un double prelevement, ecrit a la page 7 et nulle part
ailleurs.

    python micro/ma15_aiguille.py

Depuis la racine de la branche tp2-depart : le script reprend le corpus et la
question de tp2.py. Six appels, chez votre fournisseur de mesure, la ligne
FOURNISSEUR_MESURE de .env. Chez Groq, l'offre gratuite refuse tout appel de
plus de 8 000 tokens : le contexte de cet atelier en fait pres de 24 000.

Avant de lancer, predisez : sur deux essais, combien de reponses justes au
milieu ? Sortie, dans observations/b2.md : trois resultats sur deux essais, et
une phrase sur ce qu'ils ne suffisent pas a prouver.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

FOURNISSEUR = None        # None : votre fournisseur de mesure, FOURNISSEUR_MESURE
LONGUEUR = 20_000
ESSAIS = 2

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not (RACINE / "tp2.py").exists():
        print("  Lancez ce script a la racine de la branche tp2-depart : il lui faut tp2.py et son corpus.")
        return 1
    if os.environ.get("MD26_HORS_LIGNE") == "1":
        print("  MA-15 mesure un modele reel : il ne se rejoue pas hors ligne.")
        return 1
    import tp2
    from client_llm import Client, ErreurFournisseur, QuotaEpuise, charger_env

    charger_env()
    nom = FOURNISSEUR or os.environ.get("FOURNISSEUR_MESURE")
    if not nom:
        print("  Aucun fournisseur de mesure : FOURNISSEUR_MESURE dans .env (annexe C, §7).")
        return 1
    try:
        client = Client(fournisseur=nom, journal=None)
    except ErreurFournisseur as e:
        print(f"  {e}")
        return 1
    toutes = tp2.pages()
    graine = random.randrange(10_000)
    print(f"\n  {LONGUEUR} tokens, chez {nom} ({client.chaine[0].modele}), graine {graine}\n")
    bilan = {}
    for position in ("debut", "milieu", "fin"):
        justes = 0
        for k in range(ESSAIS):
            texte, _ = tp2.contexte(toutes, LONGUEUR, tp2.POSITIONS[position], graine + k)
            try:
                r = client.appeler([{"role": "system", "content": tp2.CONSIGNE},
                                    {"role": "user", "content": f"<documentation>\n{texte}\n</documentation>"
                                                                f"\n\nQuestion : {tp2.QUESTION}"}])
            except QuotaEpuise as e:
                refus = tp2.masquer(str(e.derniere if e.derniere is not None else e))
                if tp2.TROP_LONG.search(refus):
                    print(f"  {nom} refuse l'appel : le contexte est plus long que ce qu'il accepte en un"
                          f" appel. Prenez votre fournisseur de mesure.\n  Sa reponse : {refus[:200]}")
                else:
                    print(f"  {nom} ne sert pas pour l'instant : {refus[:200]}\n  Relancez plus tard.")
                return 1
            juste = bool(tp2.BONNE.search(tp2.plat(r.texte)))
            justes += juste
            print(f"  {position:<7} essai {k + 1}  {'juste' if juste else 'FAUX '}  {r.tokens_entree:>6} tokens"
                  f"  {' '.join(r.texte.split())[:60]}")
        bilan[position] = justes
    print("\n  " + "  ".join(f"{p} {n}/{ESSAIS}" for p, n in bilan.items()))
    print("  A noter dans observations/b2.md : ces trois resultats, et ce qu'ils ne suffisent pas a prouver.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
