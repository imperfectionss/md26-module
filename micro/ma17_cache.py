# -*- coding: utf-8 -*-
"""MA-17 · Le cache, en une ligne (bloc 2).

Une ligne deplace l'heure du debut a la fin de ce qui part au modele. Lisez
ce que devient le cache.

    python micro/ma17_cache.py

Cinq appels chez votre fournisseur de mesure. Le prompt systeme ne change pas
d'un appel a l'autre : les instructions de SANAD et trois pages de la
documentation, un peu plus de 2 000 tokens. Chaque appel pose une autre
question. La ligne HORODATAGE = "debut" ecrit l'heure exacte, a la seconde, en
tete du prompt systeme. Pour chaque appel, le script affiche les tokens
envoyes, tokens_caches (ceux que le fournisseur a lus dans son cache) et le
cout ; puis les totaux.

Lancez-le une fois. Changez la ligne en HORODATAGE = "fin" : l'heure passe a
la fin du dernier message. Avant de relancer, predisez tokens_caches au
deuxieme appel. Sortie, dans observations/b2.md : les deux couts totaux et le
pourcentage gagne, 1 - apres / avant.
"""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

HORODATAGE = "debut"      # la ligne a changer : "debut" ou "fin"
FOURNISSEUR = None        # None : votre fournisseur de mesure, FOURNISSEUR_MESURE

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from client_llm import Client, charger_env  # noqa: E402

PAGES = (1, 3, 7)
QUESTIONS = [
    "Combien coûte la formule Pro par mois ?",
    "Ma caisse peut-elle encaisser sans internet, et combien de temps ?",
    "À quoi sert le rapport Z, et quand le faire ?",
    "Quel jour du mois l'abonnement est-il prélevé ?",
    "J'ai été prélevé deux fois : sous combien de temps suis-je remboursé ?",
]


def systeme() -> str:
    doc = RACINE / "donnees" / "doc_sanad"
    pages = [(doc / f"page_{n:02d}.md").read_text(encoding="utf-8") for n in PAGES]
    return ("Tu es SANAD, l'assistant du support de Kounach, un logiciel de caisse. "
            "Réponds en une phrase, à partir de la documentation ci-dessous, et d'elle seule.\n\n"
            "Documentation de référence :\n\n" + "\n\n".join(pages))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if HORODATAGE not in ("debut", "fin"):
        print('  HORODATAGE vaut "debut" ou "fin".')
        return 1
    if not (RACINE / "donnees" / "doc_sanad" / "page_07.md").exists():
        print("  La documentation de SANAD manque : lancez le script sur une branche de depart a partir"
              " du TP0 bis, qui porte donnees/doc_sanad/.")
        return 1
    charger_env()
    nom = FOURNISSEUR or os.environ.get("FOURNISSEUR_MESURE")
    client = Client(fournisseur=nom, journal=None)
    base = systeme()
    print(f"\n  Chez {nom}, l'heure au {'debut du prompt systeme' if HORODATAGE == 'debut' else 'bout du dernier message'}\n")
    total, caches_total = 0.0, 0
    for rang, question in enumerate(QUESTIONS, 1):
        heure = datetime.datetime.now().strftime("Nous sommes le %d/%m/%Y à %H:%M:%S.")
        if HORODATAGE == "debut":
            messages = [{"role": "system", "content": heure + "\n\n" + base},
                        {"role": "user", "content": question}]
        else:
            messages = [{"role": "system", "content": base},
                        {"role": "user", "content": f"{question}\n\n({heure})"}]
        r = client.appeler(messages, max_tokens=60)
        total += r.cout
        caches_total += r.tokens_caches
        print(f"  appel {rang}  {r.tokens_entree:>5} envoyes  {r.tokens_caches:>5} en cache  {r.cout:.6f} $")
    print(f"\n  Total : {caches_total} tokens lus dans le cache, {total:.6f} $")
    if not total:
        print("  Un cout de 0 $ : le tarif de ce fournisseur manque dans .env (PRIX_ENTREE, PRIX_SORTIE,"
              " PRIX_CACHE, annexe C, §7).")
    print("  A noter dans observations/b2.md : le total avant, le total apres, et 1 - apres / avant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
