# Compilation

## 5. Compilation (tools/compile.ps1)
- vbsp → vvis (COMPLET, jamais -fast en livraison : sinon on voit tout à travers les murs) → vrad (-final -ldr
  -StaticPropLighting -StaticPropPolys) → bspzip (`-game` en premier) → copie dans garrysmod\maps.
- Packs Workshop : extraits (tools/extract_workshop.py, gère .gma et legacy .bin LZMA) dans un dossier DURABLE à
  chemin court (le Temp de Windows est vidé ; limite de 260 caractères de Source/bspzip/vrad).
- La liste de pack est reconstruite à chaque compilation et VÉRIFIÉE (fichiers maison présents dans le .bsp).
- Un leak = corriger avant tout (lire le .lin / la ligne « Entity … leaked »).
