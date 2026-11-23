# Contrôle qualité

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
