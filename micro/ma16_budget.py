# -*- coding: utf-8 -*-
"""MA-16 · Votre budget (bloc 2).

Ce qui part au modele au cinquieme message d'une conversation, morceau par
morceau. Sans reseau ni cle : le script rejoue la conversation b2-01 du TP2
avec l'agent de la branche, a partir des reponses capturees dans
hors_ligne/reference/.

    python micro/ma16_budget.py

Depuis la racine de la branche tp2-depart, sans rien modifier. Les lignes a
changer, si vous voulez : TACHE, une autre conversation de taches/b2.jsonl, et
MESSAGE, un autre rang. Le script affiche chaque morceau du premier appel de
ce message : son rang, son role, ses premiers mots et ses tokens estimes, a
quatre caracteres par token ; puis le poids estime des definitions d'outils,
et le compte de l'API, rejoue tel qu'il a ete capture.

Rangez vous-meme chaque morceau dans l'un des cinq postes du chapitre 5, §5.3 :
prompt systeme, definitions d'outils, documents, historique, question. Sortie,
dans observations/b2.md : cinq nombres et leur total, puis le poste que vous
attaqueriez en premier.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

TACHE = "b2-01"
MESSAGE = 5

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
os.environ["MD26_HORS_LIGNE"] = "1"      # avant tout client : rien ne part sur le reseau


def estimer(objet) -> int:
    texte = objet if isinstance(objet, str) else json.dumps(objet, ensure_ascii=False)
    return round(len(texte or "") / 4)


def contenu(m: dict) -> str:
    """Le texte d'un message, ou ses appels d'outil quand il n'a pas de texte."""
    if m.get("content"):
        return str(m["content"])
    appels = m.get("tool_calls") or []
    return " ".join(f'{a["function"]["name"]}({a["function"]["arguments"]})' for a in appels)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not (RACINE / "tp2.py").exists() or not (RACINE / "hors_ligne" / "reference").exists():
        print("  Lancez ce script a la racine de la branche tp2-depart : il lui faut l'agent du TP2"
              " et ses reponses capturees.")
        return 1
    import mesure
    import sanad
    from hors_ligne import RejeuIntrouvable

    taches = {t["id"]: t for t in mesure.charger_taches(RACINE / "taches" / "b2.jsonl")}
    if TACHE not in taches:
        print(f"  {TACHE} n'est pas dans taches/b2.jsonl : {', '.join(sorted(taches))}.")
        return 1
    messages_client = [m for s in taches[TACHE]["sessions"] for m in s]
    if not 1 <= MESSAGE <= len(messages_client):
        print(f"  {TACHE} a {len(messages_client)} messages : MESSAGE va de 1 a {len(messages_client)}.")
        return 1

    agent = sanad.construire(contexte="base")
    vus: list[dict] = []
    appeler = agent.client.appeler

    def espion(messages, outils=None, *a, **k):
        reponse = appeler(messages, outils, *a, **k)
        vus.append({"message": rang, "envoyes": [dict(m) for m in messages], "outils": outils,
                    "tokens_entree": reponse.tokens_entree})
        return reponse

    agent.client.appeler = espion
    try:
        for rang, texte in enumerate(messages_client[:MESSAGE], start=1):
            agent(texte, session=1)
    except RejeuIntrouvable:
        print("  Un appel n'a pas de reponse capturee : l'agent n'est plus celui de la capture."
              " Lancez le script sur la branche telle qu'elle est arrivee, sans modification.")
        return 1

    premier = next((v for v in vus if v["message"] == MESSAGE), None)
    if not premier:
        print(f"  Aucun appel au message {MESSAGE}.")
        return 1
    print(f"\n  {TACHE}, message {MESSAGE} : ce que le premier appel envoie au modele\n")
    total = 0
    for i, m in enumerate(premier["envoyes"], start=1):
        n = estimer(contenu(m))
        total += n
        apercu = " ".join(contenu(m).split())[:50]
        print(f"  {i:>3}  {m.get('role', '?'):<9} {n:>6}  {apercu}")
    outils = premier["outils"] or []
    n_outils = estimer(outils)
    print(f"\n       definitions d'outils : {len(outils)} outils, {n_outils} tokens estimes")
    print(f"       total estime        {total + n_outils:>6}")
    print(f"       API, tokens_entree  {premier['tokens_entree']:>6}   (rejoue, tel que capture)")
    print("\n  A noter dans observations/b2.md : vos cinq postes et leur total, puis le poste"
          " que vous attaqueriez en premier.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
