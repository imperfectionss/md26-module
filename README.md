# MD-26 · le dépôt du module

Le code partagé du module Intelligence Artificielle Agentique, FST Mohammedia.
Ce dépôt est un modèle : chaque binôme en fait sa copie privée, où il rend ses
TP. Le polycopié, partie R3, explique chaque étape.

## Faire la copie de votre binôme

1. En haut de cette page : *Use this template*, puis *Create a new repository*.
2. Nom : `md26-binome-NN`, avec le numéro de la carte de votre binôme.
   Visibilité : *Private*. Ne cochez pas *Include all branches*.
3. Dans votre copie : *Settings*, *Collaborators*, *Add people*. Ajoutez votre
   binôme, puis le compte de l'enseignant, `imperfectionss`.
4. Remplissez `BINOME.md`, puis installez votre poste avec le script
   d'installation (partie R3 du polycopié).

## Ce qu'il contient

| Fichier | Son rôle |
|---|---|
| `verifier.py` | Contrôle votre environnement et vos clés, avant chaque TP |
| `client_llm.py` | L'appel de modèle : plusieurs fournisseurs, reprise, bascule, hors ligne |
| `mesure.py` | Le banc de mesure, à partir du TP1 |
| `hors_ligne.py` | Capture et rejoue de vraies réponses |
| `atelier/` | Le workflow n8n et les tickets du TP0 |
| `observations/` | Les sorties de vos micro-ateliers |
| `.env.exemple` | Le modèle de votre `.env`, qui ne part jamais ici |
| `installer_md26.ps1`, `installer_md26.sh` | L'installation du poste, à lire avant de la lancer |

Chaque TP a sa branche de départ, `tpN-depart`, publiée ici le jour de sa
séance. À partir du TP1 bis, elle contient l'agent corrigé du TP précédent, le
même pour tous (polycopié, §R8.4).

Prof. Youssef FAKIR · FST Mohammedia · yousseff.fakirr@gmail.com
