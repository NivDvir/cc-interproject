# Site vitrine Acme

Site vitrine pour le client Acme. Onze pages statiques, generees avec Eleventy, et un
formulaire de contact qui passe par un service externe.

## Conventions

- Le contenu editorial est en francais; les noms de fichiers restent en anglais.
- Les images sont compressees avant d'etre ajoutees, jamais apres.
- La feuille de style principale est `src/styles/main.css`; pas de CSS en ligne.
- Chaque page doit passer le controle d'accessibilite avant la mise en ligne.

## Commandes

- `npm start` lance le serveur local sur le port 8080.
- `npm run build` produit le site dans `_site/`.
- `npm run check` verifie les liens internes et les images manquantes.

## A ne pas faire

Ne pas modifier les textes juridiques sans l'accord ecrit du client. Ne pas ajouter de
script de suivi: le client a refuse toute mesure d'audience.
