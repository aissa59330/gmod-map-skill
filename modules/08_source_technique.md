# Construction Source (générateur, géométrie, props)

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


## Leçons vécues (Jabiim v23 → v28)
**Génération**
- Toute nouvelle fonction tire dans son propre aléa (`IN.srng("nom")`), jamais dans le `R` global : sinon tout le reste
  de la map bouge.
- Vérifier le drapeau `static` (prop_bounds) avant d'utiliser un modèle : un modèle dynamique est refusé (clôtures en bois).
- Une ville « sombre » ne vient pas de `vrad -fast` : il manque des lumières (carrefours, places, façades).
- Remplissage des vides : disque de Poisson + test « déjà encombré » ; des boîtes nues isolées font plus vide que du vide —
  les habiller (abords, clôtures, caisses) ou mettre des avant-postes en props.
