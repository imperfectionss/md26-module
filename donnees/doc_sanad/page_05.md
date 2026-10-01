# Page 5 · Les clients et l'ardoise

*Documentation de Kounach, logiciel de gestion pour commerçants. Kounach SARL, Casablanca. Entreprise, produit et chiffres fictifs, écrits pour le module MD-26.*

## La fiche client

Un client se crée à la caisse, au moment d'une vente, ou dans « Clients ». Le
nom et un numéro de téléphone suffisent. La fiche garde l'historique des achats
et le solde de l'ardoise.

## L'ardoise

L'ardoise est le crédit que vous accordez à un client : il emporte la
marchandise et paie plus tard. À la caisse, choisissez le moyen de paiement
« Ardoise » et le client : la vente s'ajoute à sa dette. Le ticket indique le
nouveau solde.

**Le plafond.** Chaque client a un plafond d'ardoise, réglé par défaut à
500 dirhams. Au-delà, la caisse refuse la vente à crédit, sauf si un gérant la
valide avec son code. Le plafond se change dans la fiche du client.

## Le remboursement d'une dette

Quand le client paie tout ou partie de sa dette, ouvrez sa fiche, bouton
« Encaisser un règlement », et saisissez le montant et le moyen de paiement.
Un reçu s'imprime ou s'envoie par SMS. Un règlement ne s'annule que le jour
même.

## Les rappels

Kounach peut envoyer un rappel au client dont la dette dépasse un nombre de
jours que vous choisissez. Le rappel part par SMS ou par WhatsApp, avec le
montant dû et le nom du commerce, jamais le détail des achats. Les SMS de rappel
sont compris dans la formule, dans la limite de 200 par mois et par boutique ;
au-delà, ils coûtent 0,20 dirham chacun.

## Ce que le client doit accepter

Avant d'envoyer des rappels à un client, demandez-lui son accord, et notez-le
dans sa fiche : la case « Accepte les rappels » doit être cochée. Sans elle,
Kounach n'envoie rien. La page 10 explique pourquoi : un numéro de téléphone
est une donnée personnelle.

## L'export

La liste des dettes, client par client, s'exporte en tableur dans « Clients »,
rubrique Export. Elle sert à votre comptable et à vos propres relances.

## Supprimer un client

Un client dont l'ardoise est à zéro se supprime depuis sa fiche. Un client qui
doit encore de l'argent ne se supprime pas : il faut d'abord solder sa dette, ou
la passer en perte avec la validation du propriétaire. L'historique des ventes
reste dans les rapports, sans le nom du client supprimé.
