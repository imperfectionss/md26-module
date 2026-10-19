# -*- coding: utf-8 -*-
"""MA-18 · Ce que le resume a mange (bloc 2).

Une conversation de trente tours, resumee au tour 25. Trouvez ce que le
resume a perdu, et qui aurait servi.

    python micro/ma18_resume.py

Le script lit les tours 1 a 24 de micro/ma18_conversation.md, les resume en un
appel chez votre fournisseur principal, affiche le resume et l'ecrit dans
journal/ma18_resume.txt. A partir du tour 25, l'agent ne verrait plus que lui.
Pour chacun des six messages des tours 25 a 30, demandez-vous si le resume
suffit pour repondre juste.

La ligne a changer, si vous voulez : CONSIGNE. Sans reseau, le script affiche
le resume de reference capture par l'enseignant. Sortie, dans
observations/b2.md : la phrase perdue, recopiee telle que le client l'a ecrite,
avec son tour et le tour du message qui en avait besoin.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

CONSIGNE = "Tu resumes une conversation de support client en cinq phrases courtes, en francais."
FOURNISSEUR = None        # None : votre principal

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent
sys.path.insert(0, str(RACINE))


def tours(fichier: Path) -> list[tuple[int, str, str]]:
    """Les lignes du tableau « Les tours 1 a 24 » : (tour, client, SANAD)."""
    texte = fichier.read_text(encoding="utf-8")
    m = re.search(r"^## Les tours 1 à 24\s*$(.*?)^## ", texte, re.M | re.S)
    if not m:
        return []
    rendu = []
    for ligne in m.group(1).splitlines():
        cases = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cases) == 3 and cases[0].isdigit():
            rendu.append((int(cases[0]), cases[1], cases[2]))
    return rendu


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conversation = tours(ICI / "ma18_conversation.md")
    if len(conversation) != 24:
        print("  micro/ma18_conversation.md manque ou n'a pas ses 24 premiers tours.")
        return 1
    transcription = "\n".join(f"Client : {c}\nSANAD : {s}" for _, c, s in conversation)
    if os.environ.get("MD26_HORS_LIGNE") == "1":
        reference = ICI / "ma18_resume_reference.txt"
        print("\n  Sans reseau : le resume de reference, capture par l'enseignant.\n")
        print(reference.read_text(encoding="utf-8") if reference.exists() else "  (absent)")
        return 0
    from client_llm import Client, charger_env

    charger_env()
    client = Client(fournisseur=FOURNISSEUR or os.environ.get("FOURNISSEUR_PRINCIPAL"), journal=None)
    r = client.appeler([{"role": "system", "content": CONSIGNE},
                        {"role": "user", "content": transcription}], max_tokens=400)
    resume = (r.texte or "").strip()
    sortie = RACINE / "journal" / "ma18_resume.txt"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(resume + "\n", encoding="utf-8")
    print(f"\n  Le resume des tours 1 a 24, chez {r.fournisseur}, {r.tokens_entree} tokens envoyes :\n")
    print(resume)
    print(f"\n  Ecrit dans {sortie.relative_to(RACINE)}. Confrontez-le aux six messages des tours 25 a 30.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
