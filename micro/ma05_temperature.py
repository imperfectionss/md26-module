# -*- coding: utf-8 -*-
"""MA-05 · Dix fois a temperature 0 (bloc 0.5).

Le meme appel, a l'identique, dix fois, avec temperature 0. Combien de
reponses distinctes ?

    python micro/ma05_temperature.py

Changez une seule ligne, si vous voulez : FOURNISSEUR = "nvidia", ou le nom
de votre secours dans .env, pour comparer deux fournisseurs du meme modele.
Dix appels. Sortie, dans observations/b05.md : un nombre entre 1 et 10, la
date, le fournisseur et ce que vous en concluez pour vos futurs tests.
"""
from __future__ import annotations

import collections
import datetime
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client_llm import Client, charger_env  # noqa: E402

FOURNISSEUR = None        # None : votre principal, celui de FOURNISSEUR_PRINCIPAL
APPELS = 10
QUESTION = ("Un client de Kounach, un logiciel de caisse, a été prélevé deux fois ce mois-ci. "
            "Écris-lui, en trois phrases, un message d'excuse qui explique ce qui va se passer.")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    # Un seul fournisseur, sans bascule : dix reponses de deux serveurs ne
    # mesureraient plus rien.
    charger_env()
    client = Client(fournisseur=FOURNISSEUR or os.environ.get("FOURNISSEUR_PRINCIPAL"), journal=None)
    reponses, chez = [], set()
    for i in range(1, APPELS + 1):
        r = client.appeler([{"role": "user", "content": QUESTION}], temperature=0)
        reponses.append(r.texte.strip())
        chez.add(f"{r.fournisseur}, {r.modele}")
        print(f"  appel {i:>2}  {r.texte.strip()[:70]}")
        time.sleep(1)            # l'offre gratuite compte les requetes a la minute
    distinctes = collections.Counter(reponses)
    print(f"\n  {len(distinctes)} reponse(s) distincte(s) sur {APPELS}, "
          f"le {datetime.date.today().isoformat()}, chez {' et '.join(sorted(chez))}.")
    print("  A noter dans observations/b05.md : ce nombre, la date, le fournisseur\n"
          "  et ce que vous en concluez pour vos futurs tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
