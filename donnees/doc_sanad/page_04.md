# Page 4 · Le stock

*Documentation de Kounach, logiciel de gestion pour commerçants. Kounach SARL, Casablanca. Entreprise, produit et chiffres fictifs, écrits pour le module MD-26.*

## Ajouter un produit

Dans « Stock », bouton « Nouveau produit » : le nom, le prix de vente, le taux
de TVA, et si vous le voulez le prix d'achat, le code-barres et le fournisseur.
Le code-barres se scanne directement dans le champ. Un produit sans code-barres
se vend en le cherchant par son nom.

## Importer un catalogue

Pour plus de vingt produits, l'import est plus rapide. Téléchargez le modèle de
fichier dans « Stock », rubrique Importer : un tableau avec une ligne par
produit. Remplissez-le dans un tableur, enregistrez-le au format CSV, puis
importez-le. Kounach affiche les lignes refusées et la raison de chaque refus,
le plus souvent un prix vide ou un code-barres déjà utilisé. Un import ne
supprime jamais un produit existant : il ajoute ou met à jour.

## Les quantités

Chaque vente diminue le stock. Une réception de marchandise l'augmente : dans
« Stock », rubrique Réceptions, saisissez le fournisseur et les quantités
reçues. Les produits vendus au poids, comme les olives ou les épices, se
gèrent en kilogrammes avec trois décimales.

## Les alertes de seuil

Pour chaque produit, un seuil d'alerte se règle : quand la quantité passe en
dessous, le produit apparaît en rouge dans le tableau de bord, et le gérant
reçoit une notification. La liste des produits à recommander s'exporte pour être
envoyée au fournisseur.

## L'inventaire

Une fois par an au moins, comptez le stock réel. Lancez un inventaire dans
« Stock », rubrique Inventaire : Kounach fige les quantités théoriques, vous
saisissez les quantités comptées, et il calcule les écarts. Pendant
l'inventaire, la caisse continue de vendre.

## L'état des stocks

L'état des stocks donne, à une date choisie, la quantité et la valeur de chaque
produit. Sur un catalogue de plus de cinq mille produits, il peut mettre une
minute à s'afficher. S'il ne s'ouvre pas du tout, ou si la page se fige :

1. vérifiez que votre navigateur est à jour (page 9) ;
2. fermez les autres onglets ouverts sur Kounach ;
3. demandez l'état pour une seule catégorie de produits plutôt que pour tout le
   catalogue.

Si le problème continue, signalez-le au support avec le nom de votre navigateur
et l'heure de l'essai : une erreur d'affichage de l'état des stocks est traitée
comme un incident technique (page 11).

## Les catégories

Les produits se rangent en catégories et sous-catégories, qui servent aux
rapports et à l'état des stocks. Une catégorie ne se supprime que vide.
