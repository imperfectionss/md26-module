# -*- coding: utf-8 -*-
"""TP0 bis : ouvrez le capot.

    python capot.py                        une conversation, question par question
    python capot.py --tours 10             la conversation de reference, dix tours
    python capot.py --tours 20             la conversation de reference, en entier
    python capot.py --cout                 le cout cumule, lu dans journal/payload.jsonl
    python capot.py --divergence --n 20    vingt fois le meme appel, a temperature 0
    python capot.py --hors-ligne           la conversation de reference, rejouee sans reseau

L'agent repond aux questions d'un client de Kounach, un logiciel de gestion
fictif, a partir des douze pages de donnees/doc_sanad/, avec un seul outil :
chercher_documentation. Il appelle votre fournisseur de mesure
(FOURNISSEUR_MESURE dans .env) : sa fenetre tient les conversations longues,
et il n'a pas de quota journalier.

Trois fonctions sont a completer, marquees A COMPLETER. Rien d'autre n'est a
changer :

    journaliser_payload()   mesure 1, ce qui part sur le reseau
    cout_cumule()           mesure 2, le cout de la conversation
    divergence()            mesure 3, la temperature 0

Le client est cree avec journal=None : client_llm.py n'ecrit donc rien de
lui-meme, et chaque appel n'est compte qu'une fois, par votre fonction.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from client_llm import Client, charger_env

JOURNAL = Path("journal/payload.jsonl")
DOC = Path("donnees/doc_sanad")
TOURS_D_OUTIL_MAX = 4          # le critere d'arret d'un tour : au plus quatre recherches

PROMPT_SYSTEME = """Tu es l'assistant du support de Kounach, un logiciel de gestion pour \
commercants. Tu reponds aux clients a partir de la documentation de Kounach, et de \
rien d'autre.

Regles :
- Cherche dans la documentation avant de repondre, avec l'outil chercher_documentation.
- Reponds en deux a quatre phrases, dans la langue de la question.
- Cite la page sur laquelle tu t'appuies, sous la forme (page 7).
- Si la documentation ne contient pas la reponse, dis-le, et propose de transmettre \
la demande a un conseiller. N'invente jamais un delai, un prix ou une procedure."""

OUTILS = [{
    "type": "function",
    "function": {
        "name": "chercher_documentation",
        "description": ("Cherche dans les douze pages de la documentation de Kounach. "
                        "Rend les deux pages les plus proches de la requete, avec leur "
                        "numero, leur titre et leur texte. A appeler avant toute reponse."),
        "parameters": {
            "type": "object",
            "properties": {
                "requete": {"type": "string",
                            "description": "Quelques mots-cles, par exemple : double prelevement remboursement"},
            },
            "required": ["requete"],
        },
    },
}]

# La conversation de reference : vingt questions ordinaires, dans cet ordre.
# Le mode hors ligne rejoue ses reponses capturees. La derniere renvoie a la
# troisieme : le modele ne s'en souvient que si votre programme la lui renvoie.
QUESTIONS_REFERENCE = [
    "Bonjour, ou est-ce que je trouve ma facture Kounach du mois dernier ?",
    "Et le prelevement de l'abonnement, il passe quel jour ?",
    "Ce mois-ci j'ai ete preleve deux fois. Je fais comment ?",
    "Et je serai rembourse en combien de temps ?",
    "Mon caissier peut-il voir mes prix d'achat ?",
    "Comment je l'empeche d'accorder une grosse remise ?",
    "Est-ce que la caisse marche sans internet ?",
    "Pendant combien de temps, au maximum ?",
    "J'ai oublie mon mot de passe et le lien recu ne marche plus.",
    "Il reste valable combien de temps, ce lien ?",
    "Je veux passer de la formule Solo a la formule Pro. Ca se passe comment pour le paiement ?",
    "Et si je reviens a la formule Solo dans trois mois ?",
    "Mon imprimante de tickets ne marche pas avec Kounach.",
    "Elle est en Bluetooth, branchee sur un ordinateur portable.",
    "Est-ce que vous revendez mes donnees ?",
    "Et moi, je dois declarer quelque chose a la CNDP pour mes clients ?",
    "Wach n9der nsift rappel l kliyan dyali f WhatsApp ila ma khlesnich ?",
    "Ca coute combien, ces messages de rappel ?",
    "Si je resilie, est-ce que je perds toutes mes donnees ?",
    "Merci. Pour resumer : pour le double prelevement de tout a l'heure, je dois faire quoi exactement ?",
]

# La question de la mesure 3, envoyee a l'identique, sans outil.
QUESTION_FIXE = ("En une phrase : que fait Kounach quand un meme mois de l'abonnement "
                 "est preleve deux fois ?")


# --------------------------------------------------------------- l'outil
def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower())
                   if unicodedata.category(c) != "Mn")


def _pages() -> dict[int, str]:
    pages = {}
    for f in sorted(DOC.glob("page_*.md")):
        pages[int(re.search(r"page_(\d+)", f.name).group(1))] = f.read_text(encoding="utf-8")
    if not pages:
        sys.exit(f"La documentation est introuvable dans {DOC}/ : lancez capot.py "
                 f"depuis la racine du depot, sur la branche tp0bis-depart.")
    return pages


def chercher_documentation(requete: str) -> str:
    """Une recherche par mots-cles, sans accents. Chaque paragraphe de la
    documentation recoit un score : le nombre de mots de la requete qu'il
    contient. Les trois meilleurs reviennent, avec leur page, dans la limite
    de 2 400 caracteres. Le bloc 6 montrera pourquoi ce n'est pas suffisant."""
    mots = [m for m in re.findall(r"\w+", _sans_accents(requete)) if len(m) > 2]
    candidats = []
    for numero, texte in _pages().items():
        titre = texte.splitlines()[0].lstrip("# ").strip()
        for paragraphe in re.split(r"\n\s*\n", texte):
            p = paragraphe.strip()
            if not p or p.startswith("#") or p.startswith("*Documentation"):
                continue
            score = sum(_sans_accents(p).count(m) for m in mots)
            if score:
                candidats.append((score, numero, titre, p))
    candidats.sort(key=lambda c: (-c[0], c[1]))
    if not candidats:
        return json.dumps({"resultat": "aucun passage ne contient ces mots"}, ensure_ascii=False)
    extraits, taille = [], 0
    for _score, numero, titre, p in candidats[:3]:
        if taille + len(p) > 2400 and extraits:
            break
        extraits.append({"page": numero, "titre": titre, "extrait": p})
        taille += len(p)
    return json.dumps(extraits, ensure_ascii=False)


OUTILS_PYTHON = {"chercher_documentation": chercher_documentation}


# ------------------------------------------------------ ce qui part, et ce qui revient
def corps_envoye(client: Client, messages: list[dict], outils: list[dict] | None,
                 temperature: float) -> dict:
    """Le corps exact de la requete que client_llm.py envoie : le modele, les
    messages, les outils, la temperature et les reglages du fournisseur. Les
    en-tetes, eux, ne sont pas dedans, et c'est la qu'est votre cle."""
    f = client.chaine[0] if client.chaine else client._rejoue
    corps = {"model": f.modele if f else "rejeu", "messages": messages,
             "temperature": temperature}
    if f and f.max_tokens:
        corps["max_tokens"] = f.max_tokens
    if f:
        corps.update(f.options)
    if outils:
        corps["tools"] = outils
    return json.loads(json.dumps(corps))      # une copie : messages va encore changer


def journaliser_payload(corps: dict, reponse) -> None:
    """A COMPLETER, mesure 1.

    Ecrivez dans JOURNAL une ligne JSON par appel, a la suite des precedentes.
    Chaque ligne contient au moins :
        "corps"           le corps de la requete, tel quel (le parametre corps)
        "tokens_envoyes"  reponse.tokens_entree, compte par l'API
        "tokens_recus"    reponse.tokens_sortie
    Le dossier journal/ n'existe peut-etre pas encore. Jamais d'en-tete
    Authorization dans ce fichier : il contient votre cle.
    """
    pass


def prix_du_fournisseur(client: Client) -> tuple[float, float]:
    """Les prix de .env, en dollars par million de tokens : (entree, sortie)."""
    f = client.chaine[0] if client.chaine else client._rejoue
    return (f.prix_entree, f.prix_sortie) if f else (0.0, 0.0)


def cout_cumule(chemin: Path, prix_entree: float, prix_sortie: float) -> dict | None:
    """A COMPLETER, mesure 2.

    Lisez le journal ligne par ligne, et rendez un dictionnaire :
        {"par_appel": [cout de l'appel 1, cout de l'appel 2, ...],
         "total": la somme}
    Le cout d'un appel : tokens_envoyes x prix_entree + tokens_recus x
    prix_sortie, divise par un million. Les prix sont ceux de .env.
    """
    return None


def divergence(client: Client, n: int) -> int | None:
    """A COMPLETER, mesure 3.

    Envoyez n fois exactement le meme appel : le prompt systeme puis
    QUESTION_FIXE, sans outil, avec temperature=0. Rendez le nombre de
    reponses distinctes (reponse.texte). Un appel se fait ainsi :
        client.appeler(messages, temperature=0)
    """
    return None


# --------------------------------------------------------------- la boucle
def un_tour(client: Client, messages: list[dict], question: str) -> dict:
    """Un tour de conversation : la question, les recherches, la reponse."""
    messages.append({"role": "user", "content": question})
    bilan = {"envoyes": 0, "recus": 0, "appels": 0, "cout": 0.0}
    for _ in range(TOURS_D_OUTIL_MAX + 1):
        reponse = client.appeler(messages, outils=OUTILS, temperature=0)
        journaliser_payload(corps_envoye(client, messages, OUTILS, 0), reponse)
        bilan["envoyes"] += reponse.tokens_entree
        bilan["recus"] += reponse.tokens_sortie
        bilan["cout"] += reponse.cout
        bilan["appels"] += 1
        messages.append(reponse.message_brut)
        if not reponse.demande_un_outil:
            bilan["texte"] = reponse.texte
            return bilan
        for appel in reponse.appels_outils:
            fonction = OUTILS_PYTHON.get(appel["nom"])
            if fonction is None:
                resultat = json.dumps({"erreur": f"outil inconnu : {appel['nom']}"})
            else:
                resultat = fonction(**appel["arguments"])
            messages.append({"role": "tool", "tool_call_id": appel["id"], "content": resultat})
    bilan["texte"] = "(arret : quatre recherches sans reponse)"
    return bilan


def afficher(n: int, question: str, bilan: dict) -> None:
    print(f"\n[tour {n}] {question}")
    print(f"  {bilan['texte']}")
    print(f"  · {bilan['appels']} appel(s), {bilan['envoyes']} tokens envoyes, "
          f"{bilan['recus']} recus, {bilan['cout']:.6f} $")


def converser(client: Client, questions: list[str] | None) -> None:
    messages = [{"role": "system", "content": PROMPT_SYSTEME}]
    if questions is not None:
        for n, q in enumerate(questions, 1):
            afficher(n, q, un_tour(client, messages, q))
        return
    print("Posez vos questions. Une ligne vide pour finir.")
    n = 0
    while True:
        q = input("\nVous : ").strip()
        if not q:
            return
        n += 1
        afficher(n, q, un_tour(client, messages, q))


def main() -> int:
    ap = argparse.ArgumentParser(description="TP0 bis : ouvrez le capot.")
    ap.add_argument("--tours", type=int, help="jouer les N premieres questions de reference")
    ap.add_argument("--cout", action="store_true", help="le cout cumule du journal")
    ap.add_argument("--divergence", action="store_true", help="la mesure 3")
    ap.add_argument("--n", type=int, default=20, help="nombre d'appels de la mesure 3")
    ap.add_argument("--hors-ligne", action="store_true", help="rejouer la conversation de reference")
    ap.add_argument("--capturer", action="store_true",
                    help="enseignant : capturer la conversation de reference dans hors_ligne/reference")
    ap.add_argument("--fournisseur", help="un autre fournisseur que celui de mesure")
    a = ap.parse_args()

    charger_env()
    nom = a.fournisseur or os.environ.get("FOURNISSEUR_MESURE") or os.environ.get("FOURNISSEUR_PRINCIPAL")
    if a.hors_ligne:
        # Le rejeu reconnait la conversation de reference quel que soit votre
        # fournisseur : il cherche d'abord le meme modele, puis le meme contenu.
        os.environ["MD26_FOURNISSEUR"] = nom or ""
        client = Client(hors_ligne=True, journal=None)
    elif a.capturer:
        client = Client(fournisseur=nom, journal=None, capturer="hors_ligne/reference")
    else:
        client = Client(fournisseur=nom, journal=None)

    if a.cout:
        entree, sortie = prix_du_fournisseur(client)
        r = cout_cumule(JOURNAL, entree, sortie)
        if r is None:
            print("cout_cumule() est encore a completer.")
            return 1
        print(f"{len(r['par_appel'])} appels, {r['total']:.6f} $ au total "
              f"(prix de {nom} : {entree} $ et {sortie} $ par million de tokens)")
        return 0

    if a.divergence:
        if a.hors_ligne:
            print("La mesure 3 n'a pas de sens en rejeu : les reponses sont rejouees a l'identique.")
            return 1
        d = divergence(client, a.n)
        print("divergence() est encore a completer." if d is None
              else f"{d} reponse(s) distincte(s) sur {a.n} appels identiques, a temperature 0.")
        return 0 if d is not None else 1

    if a.hors_ligne or a.capturer:
        converser(client, QUESTIONS_REFERENCE[:a.tours or len(QUESTIONS_REFERENCE)])
    elif a.tours:
        converser(client, QUESTIONS_REFERENCE[:a.tours])
    else:
        converser(client, None)
    if JOURNAL.exists():
        print(f"\nJournal : {JOURNAL}")
    else:
        print("\nAucun journal ecrit : journaliser_payload() est encore a completer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
