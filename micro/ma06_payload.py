# -*- coding: utf-8 -*-
"""MA-06 · Le payload reel (bloc 0.5).

Une conversation de cinq tours avec un assistant de support. Combien de
tokens partent au tour 1 et au tour 5 ?

    python micro/ma06_payload.py

Changez une seule ligne : JOURNAL = Path("journal/ma06.jsonl"). Chaque appel
y ecrit alors une ligne, dont le champ "envoye" est le corps de la requete,
celui qui part sur le reseau, sans la cle. Ouvrez la cinquieme ligne :
qu'y trouvez-vous du tour 1 ? Cinq appels.
Sortie, dans observations/b05.md : les tokens envoyes au tour 1 et au tour 5,
et le rapport.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from client_llm import Client, charger_env  # noqa: E402

JOURNAL = None            # la ligne a changer : Path("journal/ma06.jsonl")
FOURNISSEUR = None        # None : votre principal ; le nom de votre secours s'il ne repond pas
SYSTEME = ("Tu es SANAD, l'assistant du support de Kounach, un logiciel de caisse. "
           "Réponds en deux phrases au plus.")
QUESTIONS = [
    "Bonjour, je n'arrive plus à imprimer mes tickets de caisse depuis ce matin.",
    "L'imprimante est allumée et branchée en USB.",
    "J'ai déjà redémarré la caisse, ça ne change rien.",
    "Le voyant de l'imprimante clignote en orange.",
    "D'accord. Et si ça ne marche toujours pas, qui dois-je appeler ?",
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if JOURNAL is not None:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        JOURNAL.unlink(missing_ok=True)          # une conversation par journal
    # Un seul fournisseur, sans bascule : deux tokenizers ne se comparent pas.
    charger_env()
    client = Client(fournisseur=FOURNISSEUR or os.environ.get("FOURNISSEUR_PRINCIPAL"), journal=JOURNAL)
    messages = [{"role": "system", "content": SYSTEME}]
    envoyes = []
    for tour, question in enumerate(QUESTIONS, 1):
        messages.append({"role": "user", "content": question})
        r = client.appeler(messages)
        envoyes.append(r.tokens_entree)
        print(f"  tour {tour}  {r.tokens_entree:>5} tokens envoyes   {r.texte.strip()[:60]}")
        messages.append({"role": "assistant", "content": r.texte})
    rapport = f"{envoyes[-1] / envoyes[0]:.1f}".replace(".", ",")
    print(f"\n  Tour 1 : {envoyes[0]} tokens envoyes. Tour 5 : {envoyes[-1]}. Rapport : {rapport}.")
    if JOURNAL is None:
        print("  Pour voir ce qui part : JOURNAL = Path(\"journal/ma06.jsonl\"), puis relancez.")
    else:
        print(f"  Le journal : {JOURNAL}. Sa cinquieme ligne, champ \"envoye\", est ce qui part au tour 5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
