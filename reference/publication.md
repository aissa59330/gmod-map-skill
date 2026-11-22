# Packs requis et publication — méthode générale

- Mesurer quels packs sont vraiment utilisés (faces + props + matériaux des modèles LOD).
- Moins de packs requis : garder ceux qui portent le gros (textures des murs, props importants), remplacer le reste.
  ⚠ Embarquer dans le .bsp des modèles/textures d'autres auteurs = réupload : risque de retrait Workshop ; prévenir
  l'utilisateur AVANT et préférer le remplacement par du contenu des packs requis / de base.
- Addon de la map : `maps/<map>.bsp` + `addon.json` (type map, tags), zéro Lua (le valider), < 500 Mo.
- Miniature : JPG 512×512 (capture en jeu recadrée + titre) ; description BBCode avec crédits des auteurs des packs.
- gmpublisher : 1re fois « Publish », ensuite **Update** sur l'addon existant (sinon nouvel ID).
  Éléments requis à cocher sur la page Steam. Les serveurs ajoutent l'ID à leur collection.
- **Publier soi-même en ligne de commande** (Steam ouvert, quand l'utilisateur le demande explicitement) :
  `bin/win64/gmad.exe create -folder publish/<map> -out <scratch>/<map>.gma` puis
  `bin/win64/gmpublish.exe update -id <ID> -addon <map>.gma -changes "..."` ; miniature seule :
  `gmpublish.exe update -id <ID> -icon publish/miniature_512.jpg` (pas de ré-upload de la map).
  ⚠ La note `-changes` avec des **accents est jetée en silence** (fichier mis à jour mais pas de note) → texte ASCII.
  ⚠ **Toujours copier le dernier .bsp compilé dans `publish/<map>/maps/` AVANT l'Update** (oubli vécu deux fois :
  l'utilisateur a publié l'ancienne version) et vérifier ensuite la « Taille du fichier » sur la page Workshop
  (= taille du .bsp en Mo décimaux). La description ne se change PAS en ligne de commande : il faut une session Steam
  connectée (navigateur intégré ou Chrome relié) ; sinon donner le texte BBCode prêt à coller (page
  `steamcommunity.com/sharedfiles/editdetails/?id=<ID>`, marche aussi dans Safari sur téléphone).
- **Tester la bonne version** : si l'utilisateur est abonné à l'addon, la copie Workshop passe DEVANT
  `garrysmod\maps` → désactiver l'addon (menu Addons) pour tester une compilation locale. Après un Update, Steam
  télécharge la nouvelle copie au lancement de Gmod (`steamapps/workshop/content/4000/<ID>/*.gma`, vérifier la taille).
- Mettre à jour la description quand le contenu change (ex. « contenu de base uniquement » devenu faux après passage
  au contenu embarqué) : crédits des packs + phrase « la licence ne couvre pas le contenu des autres auteurs ».
- Open source possible : licence CC BY 4.0 (attribution), sources (.vmf + générateur) sur GitHub, sans le contenu tiers.
- Description Workshop (modèle qui a marché) : `[h1]` titre ; pitch (joueurs, durée, thème) ; `[h2]` déroulé / zones ;
  `[h2]` Pour les maîtres du jeu (repères de spawn, commandes de phase, ce qui est affiché, anti-grief, « testée à N PNJ ») ;
  `[h2]` Infos techniques (aucun Lua, packs requis, nom en jeu) ; `[h2]` Open source (phrase de crédit exacte, lien
  CC BY 4.0, la licence ne couvre pas le contenu des autres auteurs) ; `[h2]` Crédits. Exemple : `reference/description_workshop.txt`.
- Note de mise à jour (Update) : sections OPTIMISATION / NOUVEAUTÉS / CORRECTIONS, une ligne par changement visible.

---

# Publication Workshop — Opération Givre Noir

## Contenu de l'addon de la map
`addons/givre_noir_map/` :
- `addon.json` (type `map`)
- `maps/givre_noir.bsp` — copié par `tools/package_map.ps1` depuis `maps_src/` (le script vérifie la taille < 500 Mo)

**Aucun Lua, aucune texture ni aucun modèle d'autres créateurs n'est inclus dans l'addon.** Les contenus
tiers sont des **éléments requis** : le Workshop les fait télécharger automatiquement aux joueurs et au serveur.

## Éléments requis à cocher sur la page Workshop (4 maximum)

Le peu de contenu pris à 4 autres packs (Venator du ciel, caisses, réservoirs, balises, textures des droïdes) est **embarqué dans le .bsp** par `tools/embed_content.py` (≈ 20 Mo, cartes de relief retirées) : ces packs ne sont plus requis.
| Addon | ID Workshop | Auteur | Utilisé pour | Taille |
|---|---|---|---|---|
| Star Wars - Imperial Materials | 1206775008 | Lord Trilobite | Textures de la base (murs, sols, grilles, portes, consoles, lumières, façade) | ~122 Mo |
| Sci-fi Props Megapack | 284266415 | Lt_C | Props (couchettes, casiers, caisses, ordinateurs, générateurs, tuyaux, bureau) | ~297 Mo |
| Star Wars - Misc Prop Pack | 1987994709 | Lord Trilobite | Consoles, panneaux muraux, cuves de bacta, chaises | ~66 Mo |
| SW Modelpack Death Star | 1518614446 | KingPommes | Panneaux muraux, écrans, cellules d'énergie, lampes | ~125 Mo |

Le reste du contenu (neige, roche, conteneurs, transformateur, fûts) vient de HL2 et est déjà livré avec Garry's Mod.

À ajouter aussi à la **collection Workshop du serveur** (sinon textures roses/noires et props « ERROR »).

## Crédits à mettre dans la description (demandés par les auteurs)
- Textures impériales et vaisseaux du ciel : **Lord Trilobite** — « Star Wars - Imperial Materials » et « Star Wars - Skybox Space Props ».
- Props sci-fi : **Lt_C** — « Sci-fi Props Megapack » (avec le soutien de PalmliX).
- Props de base : **Lord Trilobite** — « Star Wars - Misc Prop Pack », « Star Wars Rogue One Prop Pack ».
- Props de base : **KingPommes** — « SW Modelpack Miscellaneous », « SW Modelpack Death Star ».
- Map : régiment 408th Corps Cosmique.

## Vérification avant publication
1. `python generator/build_map.py` puis `python tools/validate.py` → `VALIDATION : OK`
2. `tools/compile.ps1 -Final` → pas de fuite
3. `tools/run_tour.ps1 -Iter <nom>` → logique 18/18, portes 57/57, marche 0 blocage
4. `tools/package_map.ps1` → copie du BSP dans l'addon + contrôle de taille
5. Publier `addons/givre_noir_map/` (gmpublisher ou gmad) et cocher les 4 éléments requis.

⚠ Ne jamais publier `addons/givre_noir_devtour` : c'est l'outil de test local (il téléporte et pilote le joueur).
