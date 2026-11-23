# Ambiance et effets

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
