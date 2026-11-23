# Logique d'event 100 % map (sans Lua)

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
