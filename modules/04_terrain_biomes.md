# Terrain ouvert et biomes

## Leçons vécues (Jabiim v23 → v28)
**Terrain**
- La texture du sol est choisie **par dalle de 1024** : jamais de régions bruitées à petite échelle (< ~1500) ni de texture
  non « blend » au milieu d'une autre → damier de carrés. Les variations fines passent par l'alpha (peinture).
- Un relief se fait avec le terrain (coût en plans quasi nul) ; une rivière = tracé au plus bas (Dijkstra sur la carte de
  hauteur en évitant les lieux), lit à altitude lissée, berges d'autant plus larges que le terrain est haut, gués aux
  croisements de routes ; l'enregistrer comme « piste » pour que rien ne s'y pose.
- Un mur coplanaire à un bloqueur nodraw du terrain devient invisible : le décaler à l'intérieur de la dalle percée.
