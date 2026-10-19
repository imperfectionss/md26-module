# -*- coding: utf-8 -*-
"""MA-19 · Reecrivez la description (bloc 3).

Quatre outils : trois cherchent, un escalade. Les noms des recherches ne disent
rien : recherche_a, recherche_b, recherche_c. Seule la description dit a quoi
chacun sert, et celle de recherche_a est vague expres. Deux demandes passent
a l'agent ; pour chacune, le script affiche le premier outil que le modele
demande, et ses arguments. Rien n'est execute.

    python micro/ma19_description.py

recherche_a cherche les incidents en cours. Avec sa description vague, le modele
ne le devine pas : une panne du jour part vers un autre outil. Remplacez le
texte de la ligne DESCRIPTION par une vraie description de recherche_a, puis
relancez, et regardez le choix changer. Ne touchez ni aux noms ni aux autres
descriptions.

Deux appels, un par demande, chez votre fournisseur principal. Sortie, dans
observations/b3.md : les deux outils choisis avant, les deux apres, et la phrase
de votre description qui a suffi. Deux appels ne donnent pas un taux : un modele
peut choisir autrement d'une fois sur l'autre, relancez pour voir.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client_llm import Client, charger_env  # noqa: E402

FOURNISSEUR = None        # None : votre principal, celui de FOURNISSEUR_PRINCIPAL

# La seule ligne a changer : la description de recherche_a, vague au depart.
DESCRIPTION = "Cherche des informations."

SYSTEME = ("Tu es l'assistant du support de Kounach, un logiciel de caisse. Pour "
           "chaque demande, choisis l'outil qui convient et appelle-le une fois.")

DEMANDES = [
    "Combien de temps je peux reimprimer un ticket de caisse ?",
    "Depuis ce matin, mes tickets par WhatsApp ne partent plus. Que se passe-t-il ?",
]


def _chercheur(nom: str, description: str) -> dict:
    return {"type": "function", "function": {
        "name": nom, "description": description,
        "parameters": {"type": "object", "properties": {
            "requete": {"type": "string", "description": "les mots a chercher"}},
            "required": ["requete"], "additionalProperties": False}}}


def outils() -> list[dict]:
    """Les quatre outils. Seule recherche_a porte la description a changer ; les
    trois autres sont decrits une fois pour toutes. recherche_c, les tickets
    deja clos, est le voisin plausible : c'est lui que le modele prend quand
    recherche_a ne dit rien."""
    return [
        _chercheur("recherche_a", DESCRIPTION),
        _chercheur("recherche_b", "Cherche dans la documentation publique de Kounach : modes "
                                  "d'emploi, prix et delais, le fonctionnement normal du logiciel."),
        _chercheur("recherche_c", "Cherche parmi les tickets de support deja clos et resolus, "
                                  "pour retrouver un cas semblable traite par le passe."),
        {"type": "function", "function": {
            "name": "escalader_vers_humain",
            "description": "Transmet la demande a un humain quand aucun outil ne convient ou "
                           "que la demande depasse le support automatique.",
            "parameters": {"type": "object", "properties": {
                "raison": {"type": "string"}}, "required": ["raison"],
                "additionalProperties": False}}},
    ]


def premier_outil(client: Client, definitions: list[dict], demande: str) -> tuple[str, str]:
    """Le premier outil demande par le modele, et ses arguments. Un appel qui
    echoue (le modele rend parfois un appel d'outil mal forme) est rapporte, pas
    tu : la mesure doit dire quand elle n'a rien obtenu."""
    messages = [{"role": "system", "content": SYSTEME}, {"role": "user", "content": demande}]
    try:
        reponse = client.appeler(messages, outils=definitions)
    except Exception as erreur:                               # noqa: BLE001
        return f"(echec : {type(erreur).__name__})", ""
    if not reponse.appels_outils:
        return "(aucun outil)", reponse.texte[:60]
    appel = reponse.appels_outils[0]
    return appel["nom"], str(appel.get("arguments", ""))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    charger_env()
    client = Client(fournisseur=FOURNISSEUR or os.environ.get("FOURNISSEUR_PRINCIPAL"),
                    journal=None)
    print(f"\n  Description de recherche_a : « {DESCRIPTION} »\n")
    for demande in DEMANDES:
        nom, arguments = premier_outil(client, outils(), demande)
        print(f"  {demande}")
        print(f"      -> {nom}   {arguments}\n")
    print("  A noter dans observations/b3.md : les deux outils choisis, avant et apres "
          "votre description.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
