# MA-18 · La conversation à résumer

Le gérant d'une papeterie de Témara parle avec SANAD pendant trente tours. Au
tour 25, le contexte dépasse le seuil de résumé : les tours 1 à 24 sont
remplacés par un résumé, et SANAD ne voit plus que lui pour répondre aux tours
25 à 30.

Le résumé se fait en un appel, depuis la racine du dépôt :

    python micro/ma18_resume.py

Commerce, personnes et montants sont fictifs, écrits pour le module MD-26. Les
réponses de SANAD sont celles de l'agent de départ du TP2, capturées le
19 octobre 2026 chez NVIDIA, avec le modèle `openai/gpt-oss-20b` : telles
qu'il les a écrites, erreurs comprises.

## Les tours 1 à 24

| Tour | Le client | SANAD |
|---|---|---|
| 1 | Bonjour, je tiens une papeterie à Témara, sur la formule Solo depuis juin. | Bonjour ! Vous utilisez la formule Solo depuis juin. En quoi puis-je vous aider aujourd'hui ? |
| 2 | La caisse tourne sur le vieil ordinateur portable de mon frère, posé sur le comptoir. | Pour que la caisse fonctionne correctement, l'ordinateur doit être sous Windows 10 ou macOS 12 avec au moins 4 Go de RAM (voir page 9). Vérifiez que votre vieux portable répond à ces exigences ; sinon, il faudra envisager un appareil plus récent. Si vous avez besoin d'aide pour la mise à jour ou le choix d'un nouvel appareil, je peux vous orienter vers un conseiller. |
| 3 | Je viens de racheter le stock d'une papeterie qui ferme : environ 300 articles à ajouter. | Vous pouvez ajouter ces 300 articles en une seule fois : dans « Stock », cliquez sur « Nouveau produit » ou utilisez l'option d'import d'un tableau (plus de 20 produits) (page 4). Entrez les champs requis (nom, prix, TVA, etc.) et validez. Si vous avez besoin d'aide pour préparer le fichier d'import, je peux vous guider. |
| 4 | Et si une ligne est mal remplie ? | Si une ligne est mal remplie, l'import affiche la ligne refusée avec la raison (ex. : prix vide, code-barres déjà utilisé). Vous corrigez le fichier, puis réimportez-le ; les produits existants ne sont jamais supprimés (page 4). |
| 5 | L'import peut effacer mes produits actuels ? | Non, l'import ne supprime jamais un produit existant ; il ajoute ou met à jour les articles déjà présents (page 4). |
| 6 | Beaucoup de cahiers n'ont pas de code-barres. | Vous pouvez ajouter les cahiers sans code-barres : laissez le champ vide lors de l'import ou de la saisie manuelle, et le produit se vendra en le recherchant par son nom (page 4). |
| 7 | Mon lecteur de codes-barres est branché en USB. Comment je vérifie qu'il marche ? | Ouvrez un document vide (ex. : Notepad) et scannez un produit ; le code-barres doit s'afficher automatiquement, comme si vous l'aviez tapé au clavier. Si le code apparaît, le lecteur fonctionne correctement (page 9). |
| 8 | C'est bon, il marche. | Parfait ! Vous pouvez maintenant importer vos produits sans code-barres. Si vous avez d'autres questions, je suis là. |
| 9 | Des parents d'élèves veulent payer les fournitures à la fin du mois. | Les parents peuvent régler les fournitures en fin de mois en payant la facture : 1. Envoyez-leur la facture (PDF ou imprimée) depuis « Factures ». 2. Lorsqu'ils vous transmettent le virement, le chèque ou le paiement en espèces, saisissez-le sur la facture (date, moyen) ; le statut passe à « payée » (page 6). Vous n'avez pas besoin d'attendre le prélèvement du 5 mois ; la facture est indépendante de l'abonnement. |
| 10 | Je règle tout avec ma carte bancaire, qui expire d'ailleurs fin octobre. Les SMS de rappel sont payants ? | Oui, les SMS de rappel sont inclus dans votre formule jusqu'à 200 par mois et par boutique (page 5). Au-delà, chaque SMS coûte 0,20 dirham. Votre carte bancaire expirant fin octobre, assurez-vous de la mettre à jour dans « Mon compte » pour éviter tout problème de paiement. |
| 11 | Un parent me doit déjà 450 dirhams, et il veut prendre encore 100 dirhams de fournitures. | Créez une nouvelle facture de 100 dirhams pour les fournitures supplémentaires (page 6). Le parent peut régler la facture en une fois ou payer les 550 dirhams (450 + 100) par carte bancaire, en veillant à mettre à jour la carte expirant fin octobre dans « Mon compte ». Les rappels SMS sont inclus dans votre formule (200 par mois, page 5). |
| 12 | Je monte son plafond à 800 dirhams. | Pour augmenter son plafond à 800 dirhams, ouvrez la fiche du client dans « Clients », puis modifiez le champ Plafond (le défaut est 500 dirhams). Une fois enregistré, la caisse refusera les ventes à crédit au-delà de 800 dirhams sauf validation d'un gérant (page 5). |
| 13 | Je peux envoyer un rappel aux parents qui tardent à payer ? | Oui, vous pouvez envoyer un rappel SMS aux parents dont la dette dépasse le nombre de jours que vous avez défini. Le rappel part par SMS ou WhatsApp, est inclus dans votre formule (jusqu'à 200 par mois, page 5). Assurez-vous que le client a accepté les rappels dans sa fiche. |
| 14 | Merci. | Avec plaisir ! N'hésitez pas si vous avez d'autres questions. Bonne journée ! |
| 15 | Autre chose : j'ai été prélevé deux fois le 5 octobre. Je l'ai signalé lundi 12 par le formulaire Facturation, avec les deux opérations. | Vous avez bien signalé le double prélèvement via le formulaire Facturation. La procédure de remboursement est la suivante : le support régularise la situation sous sept jours ouvrés après votre signalement (page 7). Vous recevrez donc le remboursement dans ce délai. |
| 16 | Je dois refaire une demande ? | Non, vous n'avez pas besoin de refaire la demande ; le support traitera votre signalement et régularisera le double prélèvement sous sept jours ouvrés (page 7). |
| 17 | Le soir, comment je ferme la caisse ? | Pour fermer la caisse le soir : 1. Dans le module Caisse, cliquez sur Clôture (ou Rapport Z). 2. Comptez les espèces dans le tiroir, saisissez le fond de caisse. 3. Kounach compare le montant compté au montant attendu, affiche l'écart et génère le rapport Z (page 3). |
| 18 | Je peux corriger le rapport Z si je me suis trompé ? | Non, le rapport Z ne peut pas être modifié une fois émis ; il est verrouillé pour garantir l'intégrité des données (page 3). |
| 19 | Et une vente faite par erreur hier ? | Si la vente a été faite aujourd'hui, vous pouvez l'annuler depuis l'historique (gérant ou propriétaire). Après la clôture de la journée, l'annulation n'est plus possible ; il faut alors faire un remboursement qui crée une vente négative, tout en conservant l'historique (page 3). |
| 20 | Compris. | Parfait ! N'hésitez pas si vous avez d'autres questions. |
| 21 | Internet coupe souvent dans le quartier, l'après-midi. | Pas de souci : la caisse continue de fonctionner sans connexion pendant 72 heures. Les ventes sont gardées localement et envoyées dès que la connexion revient (les paiements par carte dépendent du terminal, pas de Kounach). Au-delà de 72 h, la caisse se verrouille pour éviter une perte de données (page 3). |
| 22 | Je peux vider les données du navigateur pour que la caisse aille plus vite ? | Non, ne videz jamais les données du navigateur d'une caisse qui a des ventes en attente d'envoi ; elles seraient perdues (page 3). Si aucune vente n'est en attente, vous pouvez vider le cache, mais faites-le uniquement après avoir vérifié que tout est synchronisé. |
| 23 | En fin d'année, je dois compter le stock. Je ferme la boutique ce jour-là ? | Pas besoin de fermer la boutique ! Lancez l'inventaire dans « Stock » (rubrique Inventaire) : Kounach fige les quantités théoriques, vous saisissez les quantités réelles et il calcule les écarts. La caisse continue de fonctionner pendant l'inventaire (page 4). |
| 24 | Très bien. | Parfait ! N'hésitez pas si vous avez d'autres questions. |

## Les tours 25 à 30, après le résumé

| Tour | Le client |
|---|---|
| 25 | Mon comptable veut la liste des dettes des parents. Je l'exporte où ? |
| 26 | Nous sommes jeudi 22, et le double prélèvement n'est toujours pas remboursé. C'est normal ? |
| 27 | Je peux voir les ventes du jour sur mon téléphone ? |
| 28 | Le prochain prélèvement, c'est le 5 novembre ? Il passera sans souci ? |
| 29 | Un parent a réglé toute sa dette ce matin, en espèces. Je l'enregistre comment ? |
| 30 | Dernière chose : j'ai acheté une imprimante de tickets Bluetooth de 58 mm. Comment je la relie à ma caisse ? |
