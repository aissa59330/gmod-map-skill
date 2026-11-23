# Performance (100 joueurs, PNJ) et budgets

## 6. Optimisation pour 100 joueurs et beaucoup de PNJ (recette validée par mesures)
Ordre d'impact constaté (Givre Noir : 20 → 850+ FPS dehors ; serveur 2,39 → 1,62 ms/tick à 600 PNJ) :
1. **Visibilité** : VVIS complet ; areaportals dans chaque porte (très rentable sur une map intérieure à murs droits,
   peu sur un terrain ouvert à bâtiments ronds) ; murs droits et gros volumes en world, formes rondes/inclinées et
   petit décor en func_detail (des brushes ronds en world multiplient les zones et VVIS dure des heures).
   Extérieurs : **bloc nodraw world inscrit** dans les grands rochers/falaises/tours/silos/gros vaisseaux posés
   (cache ce qui est derrière sans compliquer le calcul) ; sous un terrain en déplacements, blocs nodraw world
   (hauteur arrondie par pas de 256, fusionnés en grands rectangles) ; **func_viscluster** sur le ciel au-dessus
   de ~2560 du sol. Les PNJ qu'aucun joueur ne voit « dorment » (IA ralentie) : couper la vue fait aussi gagner le serveur.
2. **Éclairage 100 % précalculé** : aucune light_dynamic permanente (flash 0,2 s seulement) ; clignotements = `pattern`.
3. **Distance de vue** : env_fog_controller fogstart ~1400, fogend ~8000, fogmaxdensity ~0.88, **farz ~9000**
   (au-delà, chaque PNJ lointain est dessiné). Dans le ciel 3D, garder un brouillard léger (sinon silhouettes plates).
4. **Props** : tout en prop_static (aucun prop_physics / prop_dynamic sauf nécessité) ; LOD Blender + Plumber →
   studiomdl pour les modèles les plus lourds (sommets × exemplaires) : LOD0 ≤ 2000 triangles, LOD1 50 %, LOD2 20 %,
   mêmes $cdmaterials ; collisions : solid 0 (buissons), solid 2 (caisses, barils) ; fade selon la plus grande dimension :
   < 48 : 500→750 ; < 128 : 1000→1400 ; < 300 : 1800→2400 ; < 800 : 3000→3800 ; buissons/petits rochers 1300→1800 ;
   arbres/gros rochers 3400→4500 ; bâtiments et très gros modèles : jamais. Vaisseaux du ciel 3D : décimés à
   3000–5000 triangles, échelle intégrée, en prop_static (un prop_dynamic de vaisseau = des centaines de milliers de sommets).
5. **PNJ** : le graphe de nœuds (info_node) coûte au serveur ; avec des centaines de PNJ, proposer de le **supprimer**
   (mesuré : −32 % de CPU serveur à 600 PNJ ; les PNJ avancent alors en ligne droite et peuvent buter contre les murs —
   à faire valider par l'utilisateur) ou de l'espacer fortement dehors (≥ 700). Pas de .nav = rien à faire pour les NextBots.
   Garder une option `WITH_NODES` dans le générateur et exporter quand même les positions praticables dans le .json
   (elles servent de positions de PNJ au bench). **Piège vécu** : sans `mapversion` différent, Gmod recharge l'ANCIEN
   `maps/graphs/<map>.ain` (lignes vertes avec `ai_show_connect 1` alors que le .bsp a 0 nœud) → donner un numéro
   unique à chaque génération : `vmf.map_ver = int(time.time()) // 60 % 1000000` (srctools écrase `spawn["mapversion"]`
   avec `map_ver` à l'export). Un `.ain` de 16 octets = graphe vide, normal. Vérif : `ai_show_connect 1` (solo, sv_cheats).
   Repère utile : une map de référence qui tourne bien sur le serveur de l'utilisateur (ex. rp_imperialbaseslx_v2a :
   0 nœud, 4 800 zones de visibilité) se mesure avec srctools en 1 min et tranche les débats.
6. **Effets** : actifs seulement pendant leur phase (timers/sons/rotations démarrés au `_start`, coupés au `_done`) ;
   débris d'explosion non physiques (env_shooter simulation 0) ; smokestack à débit réduit ; env_fire damagescale 0.
7. **Terrain ouvert** : déplacements puissance 3 (dalles de 1024) ; lightmap 32 sur la zone de jeu, 64 en bordure ;
   herbe automatique réduite (copie du detail.vbsp de Gmod avec densités ×0,2, clé `detailvbsp` du worldspawn).
8. **Contenu embarqué** : uniquement ce qui est utilisé, jamais un fichier qui existe déjà dans les VPK du jeu de base ;
   textures réduites et recompressées en DXT (1024 max, 512 pour ce qui ne se voit que de loin), cartes de relief retirées si besoin.
- Essayé puis abandonné (terrain ouvert) : portes + areaportals sur des bâtiments ronds (2900+ zones, VVIS > 1 h, gain
  faible, PNJ bloqués dehors car graphe calculé portes fermées) ; func_viscluster au ras des bâtiments (aucun gain).
- Comparer avec d'autres maps : lire leurs BSP avec srctools (farz, nombre de zones, herbe, props, distances de fade).
- Sortir en noclip hors de la map montre tout (normal) : tester la visibilité depuis l'intérieur.

Prompts prêts à l'emploi (optimiser une map, bench serveur, nouvelle map) : `reference/PROMPTS.md`.
Démarche d'optimisation : diagnostic sans rien modifier → mesure « avant » → optimiser par ordre d'impact →
mesure « après » aux mêmes points → tableau avant / après ; demander avant tout changement de gameplay.

## 6 bis. Mesurer (avant / après, toujours)
FPS client aux mêmes points de vue, CPU serveur sur serveur dédié local par paliers de PNJ, une seule différence entre deux
versions, rien d'autre de lourd sur le PC. Détails, pièges et conseils pour les staffs : `reference/mesures.md`.


## Leçons vécues (Jabiim v23 → v28)
**Budget de plans (la vraie limite)**
- ~60 % des plans viennent des brushes **obliques** (bâtiments tournés, sacs de sable en arc, routes goudronnées inclinées,
  cylindres) : chaque brush oblique ajoute aussi des plans de biseau. Mesurer avec un **vbsp seul sur une copie du VMF**
  (`tools/plans_bsp.ps1`, lump 1 du BSP / 20) avant toute compilation complète. Routes : terrain peint, goudron seulement
  en ville (96,7 % → 87,7 %). Petits bâtiments de remplissage : murs axiaux, toits plats, coordonnées sur une grille.
- Piste à creuser : **modéliser les maisons dans Blender** (ou un autre modeleur) et les compiler en modèles (.mdl,
  props statiques) au lieu de brushes : zéro plan, et des formes plus riches (toits, auvents, corniches) qu'une boîte
  de brushes. Garder en brushes seulement ce qui doit bloquer la visibilité ou servir d'intérieur explorable.
