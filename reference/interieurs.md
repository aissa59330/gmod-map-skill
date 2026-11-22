# Bâtiments explorables et intérieurs de qualité

Méthode éprouvée sur `rp_cw_battle_of_jabiim` (nov. 2026) : 107 pièces, ~630 meubles, escaliers et trémies, dômes cloisonnés,
granges, raffinerie, bunkers, cellules, salles préfabriquées de pack, sans un trou de collision ni un bâtiment déplacé.
Code complet : `reference/generator_jabiim/` (`interieurs.py` = le moteur, `jabiim.py` = son branchement, `vx.py` = collision
orientée des props, `build_map.py` = export avec props inclinés).

## 1. Recenser avant de toucher
Envelopper les fonctions de bâtiment du générateur (house, vault_hall, round_hall, pillbox…) pour noter type, taille, étages,
accès et nombre de props posés, lancer `build_all()` **sans écrire de VMF**, et montrer le tableau à l'utilisateur.
Pourquoi : il voit ce qui est vide, ce qui n'est pas un bâtiment (silos pleins, tours) et tranche les questions de gameplay
(creuser un silo ? meubler une cellule ?) avant qu'on modifie quoi que ce soit.
Attention : `build_all()` peut réécrire des aperçus (plans PNG) → les restaurer avec git si le recensement doit rester sans effet.

## 2. Ne rien déplacer dehors
Le générateur tire ses positions dans un aléatoire global (`R`). Tout appel `R.random()` ajouté ou retiré décale TOUT ce
qui suit (maisons, végétation…). Donc :
- l'ancien aménagement est exécuté « à blanc » (`v.prop` neutralisé) pour consommer exactement les mêmes tirages ;
- tout le nouveau tirage passe par `srng(clé du bâtiment, n° de pièce)` (générateur local, stable d'une compilation à l'autre) ;
- les décisions qui changent la géométrie (maison passée à étage) gardent le même nombre de tirages globaux ;
- vérifier : positions de tous les bâtiments identiques avant / après (comparer les recensements).

## 3. Pièces typées puis compositions
Une pièce = rectangle local (faces internes des murs) + portes + zones :
- `doors` : passages (dégagement 56 u des deux côtés) — aucun meuble, et la pièce doit rester reliée à chacune ;
- `keep` : sans meuble mais on y marche (départ et arrivée d'escalier) ;
- `solid` : on n'y marche pas (volée d'escalier, trémie) ;
- `tall_keep` : devant les fenêtres, interdit aux meubles plus hauts que l'allège.
Composition par rôle (salle, cuisine, chambre, bureau, cellier, épicerie, atelier, stockage, industrie, réunion, briefing,
archives, contrôle, commandement, serveurs, machines, interrogatoire, bunker, cellule) : meubles principaux → secondaires →
déco → petits objets posés sur le **dessus réel** du support (`max.z` du modèle). Au sol, l'origine du modèle est relevée de
`-min.z` (sinon cuisinière, canapé, comptoir s'enfoncent de 20 u). Pièce pillée (bâtiment endommagé) : une partie des meubles
manque, caisses éventrées, gravats — jamais de pièce vide « parce que le tirage l'a voulu ».
Les murs sont remplis **proportionnellement à leur longueur** (`slots`) et la composition choisit les **murs les plus longs**
d'une pièce étroite : sinon les grandes salles paraissent vides et les couloirs ne reçoivent que des barils.

## 4. Valider chaque meuble
Avant de poser : dans la pièce (2 u de jeu), hors portes / keep / solid, hors fenêtres si haut, sans recouper un autre meuble,
sous le plafond, et **inondation sur une grille de 16 u** (obstacles gonflés du rayon d'un joueur) : toutes les portes restent
reliées et ≥ 35 % du sol marchable reste accessible, sinon le meuble est refusé. Une pièce inaccessible à la fin =
`RuntimeError` : la génération échoue (c'est voulu, et ça attrape aussi les erreurs de conception).
Puis contrôle global contre toute la map (`vx.resolve`) en **boîte orientée** (8 coins + 6 plans) : avec la boîte englobante
alignée sur les axes, 57 % des meubles des maisons tournées étaient refusés à tort.
Salles préfabriquées d'un pack : le modèle entier est un obstacle plein → poser leurs meubles avec `check=False` (la validation
de pièce reste active), rectangle utile relevé sur une vue de dessus Blender caméra sous le plafond.

## 5. Étages, escaliers, cloisons
- Vrai escalier : 15 marches de 15,5 u, giron 18, trémie + garde-corps ; jamais une rampe à 42°.
- Cloisons : jamais dans l'embrasure de la porte d'entrée (décaler à `door/2 + mur/2 + 16`).
- Coût en plans : chaque brush tourné apporte ses biseaux. Une quinzaine d'escaliers + planchers ≈ +900 plans (+6,8 %).
  Estimer avant de compiler en comparant le VMF à une **référence régénérée** (worktree git du tag précédent) : le VMF
  commité peut être bien plus ancien que la dernière compilation. Après compilation, lire la ligne `planes` du log vbsp.
- Brushes droits (axiaux) = presque gratuits : portiques, passerelles, galeries surélevées, escaliers taillés en grotte.

## 6. Orientation des modèles
Convention Source : l'avant d'un modèle est +X. Vérifier sur une **planche de contrôle** (`tools/planche_orientation.py`
+ `tools/assemble_planche.py`, Blender + Plumber, un rendu trois-quarts depuis +X par modèle) et corriger les exceptions à la
main dans `ORIENT` (ex. `shelfunit01a`, `tech_city_workbench` : avant en +Y → -90). Refaire la planche pour chaque nouveau lot
de modèles ; vérifier aussi que le modèle a du sens dans la pièce (un brasero allumé n'est pas une poubelle de cuisine).

## 7. Modèles HL2 « physiques seulement »
vbsp supprime en silence (`Error! prop_static using model … Deleted`) les modèles HL2 qui ont un `prop_data` sans
`allowstatic` — même s'ils sont marqués statiques dans un fichier de tailles. Vécu : shelfunit01a, furniture_couch01a,
kitchen_counter001a, trashbin01a, wood_crate001a, oildrum001, bluebarrel001. Passer `tools/static_ok.py` sur tout nouveau
modèle HL2, et lire « Deleted » dans le log vbsp après chaque compilation.

## 8. Contrôles visuels (à regarder avant de dire « fini »)
- Vues en plan par type de pièce : `tools/plans_pieces.py pieces.json shots/interieurs` (Pillow ; vert = portes, jaune = keep,
  gris = solid, bleu = fenêtres, trait = avant du modèle).
- Façades sur 4 côtés : `tools/facades_blender.py` + `tools/assemble_facades.py`. Plumber refuse le bloc `editor` du world :
  rendre une copie du VMF sans lui. Plumber dessine mal certains `hull_piece` (toits à deux pans) : confirmé complet en jeu,
  ne pas « corriger » sur la foi de Blender seul.
- Photos en jeu : `tools/photos_jeu.ps1` + addon `jb_photos` (vues calculées depuis les positions réelles du VMF ou du
  recensement, caméra au niveau des yeux). Une photo noire = caméra dans un meuble ou un talus : la refaire avant de conclure.
- Dire précisément ce qui n'a pas été vu (bâtiments des grottes sans façade, photo trop sombre…).

## 9. Décor « raconté » réutilisable
- Engins renversés / enfoncés : `v.prop(..., tilt=(tangage, roulis))`, hauteur = sol le plus bas − min z de la boîte réellement
  inclinée − enfoncement (`wreck`).
- Portique de manutention (`gantry`), entrée de bunker enterrée décorative à porte fermée (`buried_entrance` : aucun impact
  gameplay), passerelles en caillebotis axiales, galerie haute en grotte (banc de roche + escalier taillé, éclairé).
- Bunkers : objets bas seulement (sous les meurtrières) → aucun changement de gameplay.
