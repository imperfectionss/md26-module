# -*- coding: utf-8 -*-
"""
Le jumeau Python du workflow n8n de tri de tickets. Bloc 0.

    python atelier/workflow_deterministe.py --tous
    python atelier/workflow_deterministe.py TIC-003
    python atelier/workflow_deterministe.py --tp
    python atelier/workflow_deterministe.py --tous --json
    python atelier/workflow_deterministe.py --tp --sortie mesures/avant.json

Meme logique, memes sorties, memes ruptures, en Python pur. Sans Docker, sans
reseau, sans installation. C'est le filet de securite du jour ou n8n refuse de
demarrer, et le moyen le plus rapide de verifier la veille que les six tickets
cassent bien la ou ils doivent casser.

Il ne remplace pas la demonstration n8n : dans n8n, le remplacement d'un noeud
par un appel de modele est visible au tableau, un rectangle change de couleur.
Ici on ne voit que du texte.
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.join(ICI, "donnees", "tickets.json")

LARG = 78


def charger():
    if not os.path.exists(DONNEES):
        sys.exit("Jeu de donnees introuvable : %s\n"
                 "Lancez d'abord : python atelier/generer_atelier.py" % DONNEES)
    return json.load(io.open(DONNEES, encoding="utf-8"))


# ------------------------------------------------------- les six noeuds v0
def noeud_extraction(ticket):
    """Noeud 3. Il lit le corps et le passe en minuscules."""
    return {"id": ticket["id"], "corps": ticket["corps"].lower()}


def noeud_filtrage(item, mots_cles):
    """Noeud 4. La PREMIERE categorie qui matche gagne."""
    c = item["corps"]
    for nom, mots in mots_cles.items():
        if any(m in c for m in mots):
            item["categorie"] = nom
            return item
    item["categorie"] = "autre"
    return item


def noeud_reponse(item, reponses):
    """Noeud 5."""
    item["reponse"] = reponses[item["categorie"]]
    return item


def noeud_format(item):
    """Noeud 6."""
    return {"ticket": item["id"], "categorie": item["categorie"],
            "message": item["reponse"]}


def executer(ticket, d):
    """Le workflow complet. Il leve KeyError sur un ticket sans corps,
    exactement comme le noeud Code de n8n s'arrete."""
    item = noeud_extraction(ticket)
    item = noeud_filtrage(item, d["mots_cles_v0"])
    item = noeud_reponse(item, d["reponses_types"])
    return noeud_format(item)


# ---------------------------------------------------------------- affichage
def ligne(c="-"):
    print(c * LARG)


def corps_de(t):
    return t.get("corps", None)


def jouer(ticket, d, verbeux=True):
    """Retourne (categorie, statut, erreur). Statut : reussi / echec."""
    attendu = ticket["attendu"]
    if "corps" not in ticket:
        if verbeux:
            print("  corps      : ABSENT (piece jointe : %s)" % ticket.get("piece_jointe", "?"))
            print("  resultat   : KeyError: 'corps'")
            print("  le workflow ne se trompe pas, il s'arrete.")
        return (None, "echec", "KeyError: 'corps'")

    sortie = executer(ticket, d)
    obtenu = sortie["categorie"]
    action = ticket.get("action_requise")

    # Deux conditions, pas une. Un ticket bien classe reste un echec si le
    # traiter demandait d'aller chercher quelque chose : le v0 n'agit jamais.
    if obtenu != attendu:
        statut, cause = "echec", "categorie"
    elif action:
        statut, cause = "echec", "action"
    else:
        statut, cause = "reussi", None

    if verbeux:
        print("  corps      : %s" % ticket["corps"])
        print("  attendu    : %s" % attendu)
        print("  obtenu     : %s   -> %s" % (obtenu, statut.upper()))
        if cause == "action":
            print("  bien classe, et pourtant un echec.")
            print("  il fallait : %s" % action)
            print("  le v0 n'execute aucune action. Aucune ne lui a ete demandee.")
        if statut == "echec" and ticket.get("note"):
            print("  pourquoi   : %s" % ticket["note"])
    return (obtenu, statut, None)


def entete(t):
    ligne("=")
    mur = t.get("mur")
    print("  %s%s" % (t["id"], ("   [mur : %s]" % mur) if mur else ""))
    ligne("=")


# ---------------------------------------------------------------- commandes
def cmd_tous(d, lot, json_out, sortie=None):
    if lot not in d:
        sys.exit("Les tickets de la demonstration ne sont pas dans ce depot. "
                 "Utilisez --tp, ou un identifiant de ticket.")
    tickets = d[lot]
    if json_out or sortie:
        res = []
        for t in tickets:
            cat, statut, err = jouer(t, d, verbeux=False)
            res.append({"id": t["id"], "corps": corps_de(t), "attendu": t["attendu"],
                        "obtenu": cat, "statut": statut, "erreur": err,
                        "action_requise": t.get("action_requise"),
                        "mur": t.get("mur")})
        n = sum(1 for r in res if r["statut"] == "reussi")
        texte = json.dumps({
            "_source": "workflow_deterministe.py, sorties reelles du v0",
            "score": "%d/%d" % (n, len(res)),
            "tickets": res}, ensure_ascii=False, indent=2)
        if sortie:
            # Ecrit en UTF-8 par Python : une redirection « > » de PowerShell
            # sous Windows ecrirait de l'UTF-16, illisible pour mesure.py.
            chemin = Path(sortie)
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(texte + "\n", encoding="utf-8")
            print("  SCORE : %d sur %d, ecrit dans %s" % (n, len(res), chemin))
        else:
            print(texte)
        return

    reussis = 0
    for t in tickets:
        entete(t)
        cat, statut, err = jouer(t, d)
        if statut == "reussi":
            reussis += 1
        print()
    ligne("=")
    print("  SCORE : %d sur %d" % (reussis, len(tickets)))
    ligne("=")
    if lot == "demonstration":
        print("  Ecrivez-le au tableau et laissez-le la toute la seance.")
        print()
        print("  Quatre echecs, quatre causes, une seule racine : le workflow")
        print("  ne decide rien pendant l'execution.")


def cmd_un(d, tid):
    for lot in ("demonstration", "travaux_pratiques"):
        for t in d.get(lot, []):
            if t["id"].upper() == tid.upper():
                entete(t)
                jouer(t, d)
                return
    sys.exit("Ticket inconnu : %s" % tid)


def main():
    p = argparse.ArgumentParser(
        description="Jumeau Python du workflow n8n de tri de tickets (bloc 0).")
    p.add_argument("ticket", nargs="?", help="un identifiant, par exemple TIC-003")
    p.add_argument("--tous", action="store_true", help="les 6 tickets de la demonstration")
    p.add_argument("--tp", action="store_true", help="les 24 tickets du TP")
    p.add_argument("--json", action="store_true", help="sortie machine, pour sorties_enregistrees/")
    p.add_argument("--sortie", metavar="FICHIER",
                   help="ecrit la sortie machine dans FICHIER, en UTF-8")
    a = p.parse_args()

    d = charger()
    if a.tp:
        cmd_tous(d, "travaux_pratiques", a.json, a.sortie)
    elif a.tous or not a.ticket:
        cmd_tous(d, "demonstration", a.json, a.sortie)
    else:
        cmd_un(d, a.ticket)


if __name__ == "__main__":
    main()
