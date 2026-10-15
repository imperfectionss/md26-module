# Page 3 · La caisse

*Documentation de Kounach, logiciel de gestion pour commerçants. Kounach SARL, Casablanca. Entreprise, produit et chiffres fictifs, écrits pour le module MD-26.*

## Ouvrir la caisse

Chaque journée commence par l'ouverture de la caisse : le caissier compte le
fond de caisse, la monnaie présente dans le tiroir, et le saisit. Sans
ouverture, aucune vente ne peut être encaissée.

## Encaisser une vente

Scannez les produits avec un lecteur de codes-barres, ou cherchez-les par leur
nom. La quantité se modifie en touchant la ligne. Une remise se donne en
pourcentage ou en montant, sur une ligne ou sur tout le ticket ; seuls le gérant
et le propriétaire peuvent accorder plus de 10 %.

Quatre moyens de paiement sont acceptés :

- les espèces, avec le calcul de la monnaie à rendre ;
- la carte bancaire, par un terminal de paiement compatible (page 9) ;
- le paiement mixte, une partie en espèces et le reste par carte ;
- l'ardoise : la vente est inscrite au crédit du client (page 5).

## Le ticket

Le ticket s'imprime sur une imprimante de tickets de 58 ou 80 millimètres, ou
s'envoie par SMS ou par WhatsApp au numéro du client. Il porte le nom du
commerce, son identifiant commun de l'entreprise (ICE), la date, le détail des
produits et la TVA. Un ticket se réimprime depuis l'historique des ventes,
pendant 90 jours.

## Annuler une vente

Une vente s'annule depuis l'historique, le jour même, par le gérant ou le
propriétaire. Après la clôture de la journée, on ne l'annule plus : on fait un
remboursement, qui crée une vente négative et garde la trace des deux
opérations.

## La clôture de la journée

En fin de journée, le caissier compte les espèces et lance la clôture. Kounach
compare le montant compté au montant attendu et affiche l'écart. Le rapport de
clôture, appelé rapport Z, résume les ventes par moyen de paiement et par taux
de TVA. Il ne se modifie plus une fois émis.

## Sans internet

La caisse continue de fonctionner sans connexion pendant **72 heures**. Les
ventes sont gardées sur l'appareil et envoyées dès que la connexion revient. Le
paiement par carte dépend du terminal, pas de Kounach. Au-delà de 72 heures sans
connexion, la caisse se verrouille pour éviter une perte de données : il suffit
de la reconnecter. Ne videz jamais les données du navigateur d'une caisse qui a
des ventes en attente d'envoi : elles seraient perdues.

## Plusieurs caisses

La formule Pro autorise trois caisses dans la même boutique, la formule
Multi-boutiques trois par boutique. Chaque caisse a sa propre ouverture et sa
propre clôture.
