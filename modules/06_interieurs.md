# Bâtiments explorables et intérieurs

## 6 quater. Bâtiments explorables et intérieurs
Lire `reference/interieurs.md` dès qu'il faut meubler, rendre explorables ou densifier des bâtiments. L'essentiel :
- **recenser d'abord** (tableau type / taille / étages / accès / intérieur montré à l'utilisateur) ;
- **ne rien déplacer dehors** (tirage global inchangé, tirage local stable par bâtiment et par pièce) ;
- pièces typées + composition par rôle, chaque meuble **validé** (pièce, portes, fenêtres, accès), pièce inaccessible =
  la génération échoue, puis contrôle global en **boîte orientée** ;
- vrais escaliers (marches ≤ 16) mais chaque brush tourné coûte des plans : estimer avant de compiler ;
- avant des modèles vérifié sur une planche Blender ; modèles HL2 « physiques seulement » écartés (`tools/static_ok.py`) ;
- plans par pièce, façades 4 côtés et photos en jeu **regardés** avant de dire que c'est fini.
Moteur et outils : `reference/generator_jabiim/`, `reference/tools/` (plans_pieces, planche_orientation, facades_blender,
check_server, photos_jeu, static_ok), addons `jb_check`, `jb_photos`.
