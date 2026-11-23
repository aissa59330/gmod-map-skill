# Level design : structure, circulation, lignes de vue

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
