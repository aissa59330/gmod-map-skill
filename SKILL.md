---
name: gmod-map
description: Concevoir, générer, contrôler et optimiser de A à Z une map Garry's Mod (Source) d'event ou de RP, surtout Star Wars Clone Wars : direction artistique, level design, terrain et biomes, villes, bâtiments et intérieurs, narration de bataille, ambiance (sons, météo), logique d'event 100 % map (sans Lua), compilation vbsp/vvis/vrad, score qualité, anti-répétition, benchmarks, publication Workshop. À utiliser dès que l'utilisateur veut faire, reprendre, améliorer, meubler, vérifier, optimiser ou publier une map Gmod / Source (VMF, BSP, Hammer, props, FPS, trous de collision, Workshop), même s'il ne dit pas « skill ».
---

# Studio de maps Garry's Mod

**Rôle : designer d'abord, générateur ensuite.** On conçoit un lieu (histoire, fonction, style, parcours), on le
construit avec le générateur Python, puis on le juge et on le retravaille avant de le montrer.
Méthode éprouvée sur « Opération Givre Noir » (map Clone Wars 11 phases, 100 joueurs, ~1 h), puis sur Vexis,
Triple Front et Jabiim (terrain ouvert, ville vivante, intérieurs meublés).
**Ne pas recopier ce design** : réutiliser la MÉTHODE et les outils, le tracé doit être celui que l'utilisateur demande.

## Niveau visé
Rivaliser avec les **meilleures maps communautaires de Garry's Mod** : un lieu conçu par une équipe de level designers
et d'environment artists, jamais un terrain avec des bâtiments posés dessus. Les anciennes maps du skill ne sont
**pas** des références de qualité : Jabiim est en dessous du niveau voulu ; Vexis (rp_cw_arsenal_vexis, Workshop
3843123548) est un **plancher** correct mais loin d'être parfait. On ne s'arrête jamais à « aussi bien que Vexis ».
**Une map qui compile, sans trou et fluide n'est PAS une map réussie.** Elle l'est quand chaque secteur passe la grille
qualité (module 11) sans aucun motif interdit.

**Motifs interdits** (chacun = la zone est retravaillée avant de dire « fini ») :
bâtiments cubiques ou copiés · intérieurs vides · terrain plat ou relief en bosses sans logique · secteurs entassés ou
vides · paysage sans profondeur (pas de premier plan / arrière-plan) · décor pauvre (sol nu, murs propres, aucun
détail) · secteurs sans identité visuelle · zone sombre ou lumière plate · répartition en grille ou trop régulière ·
aspect « généré ». La performance est prioritaire, mais **n'excuse jamais un décor pauvre** : chercher la solution qui
garde la richesse (modèles au lieu de brushes, fondus, occulteurs, budget par zone).

## Règles absolues
- Langue de l'utilisateur partout (tableaux compris). Décisions par **questions à choix multiples**.
- **Uniquement en local** ; jamais le serveur de l'event ni ses fichiers ; rien modifier dans Gmod hors `garrysmod\maps\`
  (+ addon de test temporaire). **Ne jamais fermer le Gmod de l'utilisateur** ; ne rien lancer (Gmod, bench, compilation
  lourde) pendant qu'il joue ; ne tuer que les processus lancés par nos outils.
- **Demander avant d'installer** quoi que ce soit. S'arrêter et expliquer après 3 échecs identiques.
- **Toujours dire** ce qui est mesuré, ce qui est observé sur image, ce qui est estimé, et ce qui reste à tester en jeu.
- Projet dans un **dossier durable**, en git, **commit avant chaque grosse passe** ; état du projet tenu à jour (module 16).
- Respecter les limites de quota/budget données par l'utilisateur (vérifier l'usage régulièrement).

## Pipeline (adapter le niveau à la demande)
| # | Étape | Livrable | Modules |
|---|---|---|---|
| 1-2 | Besoin, contraintes | brief (QCM) + 2-3 références visuelles | 01 |
| 3 | Direction artistique | identité de la planète et de chaque secteur | 05, 07 |
| 4-5 | Plan global, secteurs | plan, itinéraires, lieux RP, budget par zone | 03, 07, 14 |
| 6 | Terrain | relief, eau, biomes | 04 |
| 7-8 | Bâtiments, aménagement | architecture, intérieurs, décor raconté, ambiance | 05, 06, 07, 10 |
| 9-10 | Intégration, compilation | VMF puis BSP (rapide → lumière → finale) | 08, 09, 13 |
| 11-12 | Performance, tests | audit, benchmarks comparatifs, trous, photos | 11, 14 |
| 13-14 | Corrections, validation | score qualité sans régression | 11 |
Niveaux : **retouche** (9-14) · **zone** (4-14 sur une zone) · **map complète** (1-14). **Reprendre un projet** : module 16 d'abord.
L'utilisateur intervient 3 fois : brief, validation du plan (une image), test final. Le reste se règle sans lui.

## Table de routage (ne charger que ce qui sert)
| Tâche | Lire |
|---|---|
| Nouvelle map / cadrage | `modules/01_cadrage.md`, `modules/02_projet_pipeline.md` |
| Plan, parcours, combat, lignes de vue | `modules/03_level_design.md` |
| Relief, eau, végétation, textures du sol | `modules/04_terrain_biomes.md` |
| Architecture, style, villes | `modules/05_architecture_villes.md` (+ `reference/style_vexis.md`) |
| Intérieurs, étages, meubles | `modules/06_interieurs.md` (+ `reference/interieurs.md`) |
| Générateur, géométrie, props, chemins de fichiers | `modules/08_source_technique.md` |
| Phases, boutons, relais (sans Lua) | `modules/09_logique_event.md` |
| Effets, sons, ambiance | `modules/10_ambiance_effets.md` |
| Vérifier, juger, livrer | `modules/11_controle_qualite.md` |
| Aperçus Blender, LOD | `modules/12_apercus_blender.md` |
| Compiler | `modules/13_compilation.md` |
| FPS, serveur, PNJ, budgets, mesures | `modules/14_performance.md` (+ `reference/mesures.md`, `reference/METHODE_BENCH_SERVEUR.md`) |
| Packs, Workshop | `modules/15_publication.md` (+ `reference/publication.md`) |
| Reprendre un projet existant | `modules/16_reprise_projet.md` |
| Rappel détaillé des règles de travail | `modules/00_regles_utilisateur.md` |
Prompts prêts à l'emploi : `reference/PROMPTS.md`. Code de référence : `reference/` (voir `reference/LISEZMOI.md`).
