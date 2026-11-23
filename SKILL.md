---
name: gmod-map
description: Créer de A à Z une map Garry's Mod (Source) d'event multijoueur, générée en Python (srctools), compilée en ligne de commande (vbsp/vvis/vrad), vérifiée en jeu et optimisée pour 100 joueurs, avec logique de phases 100 % map (sans Lua), effets, sons maison, bâtiments explorables meublés et publication Workshop. À utiliser dès que l'utilisateur veut faire, modifier, optimiser, meubler, vérifier ou publier une map Gmod / Source (VMF, BSP, Hammer, vbsp/vvis/vrad, props, intérieurs, trous de collision, FPS, Workshop), même s'il ne dit pas « skill ».
---

# Map Garry's Mod d'event — méthode complète

Méthode éprouvée sur « Opération Givre Noir » (map Clone Wars 11 phases, 100 joueurs, ~1 h), puis sur Vexis,
Triple Front et Jabiim (terrain ouvert, ville vivante, intérieurs meublés).
Code de référence complet et fonctionnel : `reference/` (générateur `reference/generator/`, outils `reference/tools/`,
addons de test `reference/addons/`, ancien CLAUDE.md du projet `reference/CLAUDE_givre_noir.md`),
moteur d'intérieurs `reference/generator_jabiim/`. Fiches : `reference/interieurs.md`, `mesures.md`, `style_vexis.md`, `publication.md`.
**Ne pas recopier ce design** : réutiliser la MÉTHODE et les outils, le tracé doit être celui que l'utilisateur demande.

## 0. Avant de commencer (demander à l'utilisateur)
- Thème, nombre de joueurs, durée, nombre de phases / objectifs, camps (attaquants / défenseurs).
- Contraintes du serveur : **addons Lua refusés ?** (presque toujours : tout faire en entités de map),
  **nombre max de packs Workshop requis** (Givre Noir : 4 max), **taille max** (souvent 1 Go).
- Ce qui est affiché à l'écran (souvent : rien, la narration est faite en direct ; exceptions demandées explicitement).
- Packs Workshop de contenu autorisés (textures / props) ; le style visuel attendu (captures).
- Règles absolues : ne rien modifier dans le dossier Gmod hors `garrysmod\maps\` (+ addon de test temporaire),
  jamais le serveur de l'event, pas de sv_cheats en ligne, **ne jamais fermer le Gmod de l'utilisateur**,
  demander avant d'installer quoi que ce soit, s'arrêter et expliquer après 3 échecs identiques.
- Créer le projet dans un **dossier durable** (pas un dossier temporaire de session) et l'initialiser en git ;
  commit avant chaque grosse passe.

## 1. Architecture du projet
```
projet/
  generator/   build_map.py (VMF via srctools), zones.py (salles = "spaces" en boîtes), entities.py (logique),
               props.py / dressing.py / kit.py (habillage), fx.py (effets), minigames.py, optim.py, nodes.py, areaportals.py
  tools/       compile.ps1, make_sounds.py, make_signs.py, embed_content.py, extract_workshop.py, diag.py, bench.ps1, package_map.ps1
  addons/      addon de test (tournée, bench) — JAMAIS publié ; addon de la map (bsp + addon.json, zéro Lua)
  compile_game/ profil de compilation (gameinfo + cfg/mount.cfg qui monte les packs extraits)
  maps_src/ logs/ docs/ shots/
```
Principe : **on ne touche jamais le .vmf à la main**, tout vient du générateur (régénérable, versionnable).
Si l'utilisateur veut passer sur Hammer, lui expliquer que la régénération écraserait ses retouches.

## 1 bis. Concevoir « rectangulaire et optimisé » dès le départ (préférence de l'utilisateur)
- **Plan général en « − », pas en « + »** : la map est une **longue bande rectangulaire** où les zones se suivent
  sur **un seul axe** (départ à un bout, objectif final à l'autre), en exploitant la longueur maximale (~32 000 u)
  plutôt que la largeur. Pas de plan en croix / en étoile avec des branches dans toutes les directions.
  Les « 3 voies » d'une zone restent côte à côte dans la bande (voie principale + 2 flancs parallèles).
  Avantages : progression claire, chaque zone ne voit que la précédente et la suivante (visibilité très bien
  découpée), spawns de phase faciles, extérieur long pour le combat aérien. Si la longueur ne suffit pas, replier la bande
  en « U » (deux bandes parallèles séparées par un mur plein), jamais en croix.
- **Formes rectangulaires** : salles, bâtiments, couloirs et cours en boîtes alignées sur la grille, angles à 90°,
  couloirs droits avec virages à angle droit. C'est ce qui rend VVIS rapide et la visibilité bien découpée.
- **Structure en world, décor en func_detail** : seuls les murs droits, sols et plafonds porteurs sont en world ;
  tout ce qui est rond, incliné ou petit (piliers octogonaux, rochers, rampes, garde-corps, machines) en func_detail,
  avec si besoin un bloc nodraw world inscrit dedans pour qu'il cache quand même la vue.
- **Intérieurs fermés** reliés par des **portes + areaportals** (dans l'épaisseur de la porte) : le plus gros gain de
  FPS sur une map de base / bâtiments. Règle « couloir étroit → grande salle → couloir étroit », jamais deux grandes
  salles qui se voient directement.
- **Extérieurs découpés en secteurs** reliés par des cols / goulots (falaises pleines avec bloqueur nodraw), plutôt
  qu'une seule immense plaine ; ciel couvert par func_viscluster.
- À éviter : bâtiments ronds en world (des milliers de zones, VVIS de plusieurs heures), grandes plaines sans relief
  qui voient tout, brushes inclinés en world.
- Sur un terrain ouvert imposé (style Vexis), appliquer la recette « terrain ouvert » de la section 6 au lieu des areaportals.

## 2. Construction (generator)
- Chaque salle = une boîte d'air ; le générateur fait le CSG (murs de 16 min., tout sur la grille de 16, ±16384 max).
- Échelle : joueur 32×32×72 ; portes ≥ 192×160 ; couloirs 192–320 ; grandes salles 2048–4096 ; marches 8×16.
- Combat de masse : 3 voies par zone, ≥ 3 entrées par objectif, couverts, verticalité ; alterner couloir étroit → grande salle.
- Extérieurs (sky=True) assez grands pour le combat aérien ; plusieurs secteurs reliés par un col si on manque de place
  (la limite ±16384 bloque un axe : s'étendre sur l'autre).
- Décor en `func_detail`, nodraw sur les faces cachées, lightmapscale grossier sur les grandes surfaces extérieures.
- Placement des props : bbox dans la salle, posé sur un sol / bloc / autre prop, jamais au-dessus d'une fosse (le poser au
  fond ou le retirer), jamais dans un mur. Faire un **contrôle automatique** (flotte / dans un mur / dans un bloc) avant livraison.
- **Exactitude des chemins** : ne jamais écrire un chemin de modèle, de texture ou de son de mémoire. Le vérifier
  (fichier de tailles des props, listing des VPK, dossiers des packs extraits) : un chemin inventé = prop absent ou
  texture rose, et une liste noire / un remplacement qui ne servent à rien.
- Textures : orientation des panneaux = `-face.normal()` de srctools (sinon texte en miroir) ; textures maison en VTF
  (Pillow + srctools, DXT1), embarquées par bspzip.

## 3. Logique 100 % map (aucun Lua)
- Une phase = `logic_relay` `<pfx>_phase_<n>_start` / `_done` (once). Démarrage auto par `logic_auto`.
- Entités utiles : func_door (areaportal DANS l'épaisseur de la porte), func_button (1024 use, 32 toggle → OnIn/OnOut,
  2048 verrouillé), math_counter (OnHitMax / OnChangedFromMax), logic_branch(+listener), logic_case (16 cas max),
  logic_timer (inputs RefireTime, LowerRandomBound…), game_text (seul affichage possible), ambient_generic
  (spawnflags 1 partout, 16 démarre en silence+boucle, 32 non bouclé ; 48 = silence+non bouclé).
- Compte à rebours affiché : relais avec AddOutput « message … » + Display chaque seconde (pas de virgule dans le texte).
- Pièges vécus :
  - `momentary_rot_button` (molettes à tenir) : peu fiable (angle qui bascule à 180°, OnFullyOpen qui ne part pas).
    Préférer leviers/boutons simples + délai ; si molette : course < 180 et déclenchement de secours par la sortie Position.
  - Lock/Unlock sur un bouton en mouvement le casse : garder l'état dans un logic_branch.
  - Un commentaire Python qui avale la fin d'une ligne de kwargs (StartDisabled…) = bug silencieux : relire.
  - Tester chaque mini-jeu avec un vrai maintien de [E] (hook StartCommand IN_USE), pas avec Fire/Use.
- Anti-grief : sur toutes les entités `gmod_allowphysgun 0` + `gmod_allowtools "aucun"` (Sandbox et dérivés).
- Lancer une phase pour tester : `lua_run ents.FindByName("<pfx>_phase_N_done")[1]:Fire("Trigger")` (console serveur).

## 4. Effets et ambiance (sans tuer les FPS)
- Briques réutilisables (voir `reference/generator/fx.py`) : GROS BOUM (env_explosion ×3 décalées sans dégâts,
  light_dynamic flash 0,2 s éteinte au spawn, env_shake, env_physexplosion, env_shooter gibs, env_fire damagescale 0,
  env_smokestack), arcs (point_tesla), vapeur (env_steam), alarme locale (func_rotating + sprite + klaxon),
  porte lourde (OnOpen → son + vapeur + secousse), vaisseaux dans le ciel 3D (func_movelinear + prop_dynamic, échelle 1/16).
- Rythme de chaque objectif : ça monte (tension) → ça pète → ça reste (fumée, feu).
- Final spectaculaire possible : ciel/brouillard qui changent (AddOutput topcolor sur env_skypaint nommé, SetColor sur le fog),
  env_beam depuis le ciel (bombardement), env_fade (flash blanc, assombrissement rouge modulé), explosions en vagues
  de plus en plus grosses (logic_case + logic_timer dont on réduit les bornes).
- Jamais de light_dynamic permanentes (FPS) ; lumières clignotantes = `light` nommée avec `pattern` (précalculé).
  Max 4 styles de lumière par face : peu de lumières nommées qui se recouvrent.
- Sons : uniquement ceux des VPK de Gmod/HL2 (vérifier qu'ils existent en listant les VPK) ou maison (TTS + effet
  droïde, mp3 fourni par l'utilisateur) embarqués dans le .bsp. Voix et alarmes « partout » = spawnflags 1.
- Toute nouvelle entité doit être DANS une salle (sinon leak) : vérifier les origines par script avant de compiler.

## 4 bis. Prévisualisation Blender (AVANT de compiler, à chaque grosse modification du tracé)
- Outils : **Blender** (4.x/5.x) + addon **Plumber** (import VMF/MDL ; demander à l'utilisateur avant d'installer).
- Commande : `blender -b -P tools/preview_blender.py -- maps_src/<map>.vmf shots/iter_N/blender/`
  (référence : `reference/tools/preview_blender.py`). Opérateur d'import : `bpy.ops.import_scene.plumber_vmf`
  (le lister dans `dir(bpy.ops.import_scene)` ; activer l'extension `bl_ext.user_default.plumber` si besoin).
  Plumber refuse le bloc `editor` au niveau du world : en importer une copie nettoyée. Échelle Plumber : 0,01.
- Rendus : 1 vue de dessus orthographique de toute la map + 1 vue par zone. **Regarder les images** :
  proportions, connexions, salles qui se chevauchent, 3 voies par zone, ≥ 3 entrées par objectif.
- Complément rapide sans Blender : plan SVG de dessus (`reference/tools/plan_svg.py`, lit le .json exporté par le générateur).
- Blender sert aussi aux **LOD des props** : import MDL (Plumber) → Decimate → export SMD → studiomdl
  (`reference/tools/make_lod_props.py`, puis `fix_lod_qc.py` pour les $cdmaterials).
- Ensuite seulement : compilation, puis tournée en jeu (les rendus Blender ne remplacent pas la vérification en jeu).

## 5. Compilation (tools/compile.ps1)
- vbsp → vvis (COMPLET, jamais -fast en livraison : sinon on voit tout à travers les murs) → vrad (-final -ldr
  -StaticPropLighting -StaticPropPolys) → bspzip (`-game` en premier) → copie dans garrysmod\maps.
- Packs Workshop : extraits (tools/extract_workshop.py, gère .gma et legacy .bin LZMA) dans un dossier DURABLE à
  chemin court (le Temp de Windows est vidé ; limite de 260 caractères de Source/bspzip/vrad).
- La liste de pack est reconstruite à chaque compilation et VÉRIFIÉE (fichiers maison présents dans le .bsp).
- Un leak = corriger avant tout (lire le .lin / la ligne « Entity … leaked »).

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

## 6 ter. Style, ville vivante, immeubles accessibles (terrain ouvert)
Restyler sans réécrire (MAT_REMAP / PROP_SWAP), immeubles à socle creux praticable, limite des 65 536 sommets, ville qui
raconte une histoire, lieux RP nommés, monde vivant plafonné, matériaux de modèle sur des brushes, photos de présentation
automatiques : `reference/style_vexis.md` (modules dans `reference/generator_tf/`).

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

## 7. Vérification (check-list, dans cet ordre)
1. **Génération** : le générateur passe (aucune RuntimeError d'accessibilité), connectivité « aucun lieu injoignable ».
2. **Rien n'a bougé sans le vouloir** : positions des bâtiments identiques avant / après (recensement), sinon expliquer.
3. **Compilation** : pas de leak ; lire dans le log vbsp les lignes `Deleted` (props supprimés) et `planes` (viser < 90 %).
4. **Trous de collision** : `tools/check_server.ps1` (addon `jb_check`, serveur dédié local fenêtre réduite) → 0 trou, 0 chute.
   Les ouvertures VOULUES (puits vers des cavernes) sont exclues de jb_check et contrôlées à part : rayons à travers
   chaque puits qui listent les couches traversées (addon `jb_puits`) → le fond doit être atteint. Vécu : un monde
   décalé (cavernes à -3840) dont le `carve` n'était pas décalé laissait un plafond plein à -1584 dans les 3 puits,
   invisible pour jb_check (les rampes arrêtaient ses rayons) pendant des versions entières.
5. **Images** : vues en plan / Blender, puis photos en jeu (`tools/photos_jeu.ps1`) aux endroits modifiés ; refaire toute
   vue noire ou mal cadrée.
6. **Compte rendu** : ce qui est vérifié, ce qui ne l'est pas, ce que l'utilisateur doit tester lui-même en jeu.
Addon de test toujours copié puis retiré ; Gmod lancé par nos outils seulement quand l'utilisateur ne joue pas, et on ne
ferme que le PID qu'on a lancé (jamais son Gmod).

## 8. Packs requis et publication
Mesurer les packs vraiment utilisés, en garder le moins possible, ne jamais réuploader le contenu d'autres auteurs sans
prévenir, addon de la map sans Lua, **copier le dernier .bsp avant chaque Update** et vérifier la taille sur la page
Workshop, note de mise à jour en ASCII. Tout le détail (gmad / gmpublish, description BBCode, open source CC BY 4.0) :
`reference/publication.md`.

## 9. Façon de travailler avec l'utilisateur
- Il teste en jeu et envoie des captures (+ `getpos`) : corriger exactement ce qui est montré, recompiler, dire quoi tester.
- Réponses courtes, dans la langue de l'utilisateur (en français s'il écrit en français, y compris les tableaux) ; commandes prêtes à copier ; jamais prétendre avoir vérifié en jeu ce qui ne l'a pas été.
- Respecter les limites de quota/budget données par l'utilisateur (vérifier l'usage régulièrement).
- Tenir un journal d'itérations (`logs/iterations.md`) et un document de narration pour les organisateurs.

## 10. Erreurs à ne pas refaire (vécu Jabiim, v23 → v28)
**Budget de plans (la vraie limite)**
- ~60 % des plans viennent des brushes **obliques** (bâtiments tournés, sacs de sable en arc, routes goudronnées inclinées,
  cylindres) : chaque brush oblique ajoute aussi des plans de biseau. Mesurer avec un **vbsp seul sur une copie du VMF**
  (`tools/plans_bsp.ps1`, lump 1 du BSP / 20) avant toute compilation complète. Routes : terrain peint, goudron seulement
  en ville (96,7 % → 87,7 %). Petits bâtiments de remplissage : murs axiaux, toits plats, coordonnées sur une grille.
- Piste à creuser : **modéliser les maisons dans Blender** (ou un autre modeleur) et les compiler en modèles (.mdl,
  props statiques) au lieu de brushes : zéro plan, et des formes plus riches (toits, auvents, corniches) qu'une boîte
  de brushes. Garder en brushes seulement ce qui doit bloquer la visibilité ou servir d'intérieur explorable.
**Terrain**
- La texture du sol est choisie **par dalle de 1024** : jamais de régions bruitées à petite échelle (< ~1500) ni de texture
  non « blend » au milieu d'une autre → damier de carrés. Les variations fines passent par l'alpha (peinture).
- Un relief se fait avec le terrain (coût en plans quasi nul) ; une rivière = tracé au plus bas (Dijkstra sur la carte de
  hauteur en évitant les lieux), lit à altitude lissée, berges d'autant plus larges que le terrain est haut, gués aux
  croisements de routes ; l'enregistrer comme « piste » pour que rien ne s'y pose.
- Un mur coplanaire à un bloqueur nodraw du terrain devient invisible : le décaler à l'intérieur de la dalle percée.
**Génération**
- Toute nouvelle fonction tire dans son propre aléa (`IN.srng("nom")`), jamais dans le `R` global : sinon tout le reste
  de la map bouge.
- Vérifier le drapeau `static` (prop_bounds) avant d'utiliser un modèle : un modèle dynamique est refusé (clôtures en bois).
- Une ville « sombre » ne vient pas de `vrad -fast` : il manque des lumières (carrefours, places, façades).
- Remplissage des vides : disque de Poisson + test « déjà encombré » ; des boîtes nues isolées font plus vide que du vide —
  les habiller (abords, clôtures, caisses) ou mettre des avant-postes en props.
