# -*- coding: utf-8 -*-
"""MA-04 · Comptez vos tokens (bloc 0.5).

La meme phrase en francais, en anglais et en arabe : combien de tokens
chacune coute-t-elle ? Le compte vient de l'API, qui le rend avec chaque
reponse (usage.prompt_tokens) : c'est celui qu'on vous facture.

    python micro/ma04_tokens.py

Changez une seule ligne, si vous voulez : une phrase de PHRASES, ou une
quatrieme, en darija par exemple. Quatre appels, chez votre fournisseur
principal. Sortie, dans observations/b05.md : trois nombres et le rapport
entre le plus grand et le plus petit.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client_llm import Client, charger_env  # noqa: E402

# Un seul fournisseur, sans bascule : deux tokenizers ne se comparent pas. Si
# votre principal ne repond pas, mettez ici le nom de votre secours.
FOURNISSEUR = None        # None : votre principal, celui de FOURNISSEUR_PRINCIPAL
PHRASES = {
    "francais": "Mon abonnement a été prélevé deux fois ce mois-ci : quand serai-je remboursé ?",
    "anglais": "My subscription was charged twice this month: when will I be refunded?",
    "arabe": "تم خصم اشتراكي مرتين هذا الشهر: متى سأسترد المبلغ؟",
}


def tokens_envoyes(client: Client, texte: str) -> tuple[int, str]:
    """Les tokens de la requete entiere, tels que le fournisseur les compte."""
    r = client.appeler([{"role": "user", "content": texte}], max_tokens=16)
    return r.tokens_entree, r.fournisseur


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    charger_env()
    client = Client(fournisseur=FOURNISSEUR or os.environ.get("FOURNISSEUR_PRINCIPAL"), journal=None)
    # La requete n'envoie pas que votre phrase : le role, et les marques qui
    # entourent chaque message. Un message d'un seul mot donne cette enveloppe.
    enveloppe, fournisseur = tokens_envoyes(client, "ok")
    enveloppe -= 1
    print(f"\n  Chez {fournisseur}, l'enveloppe d'un message vaut {enveloppe} tokens.\n")
    comptes = {}
    for langue, phrase in PHRASES.items():
        total, fournisseur = tokens_envoyes(client, phrase)
        comptes[langue] = total - enveloppe
        print(f"  {langue:<10} {comptes[langue]:>4} tokens   ({len(phrase)} caracteres)  {phrase}")
    grand, petit = max(comptes.values()), min(comptes.values())
    if petit:
        rapport = f"{grand / petit:.2f}".replace(".", ",")
        print(f"\n  Rapport du plus grand au plus petit : {rapport}")
    print("  A noter dans observations/b05.md : les trois nombres et ce rapport.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
