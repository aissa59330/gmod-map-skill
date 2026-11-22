# Modules Triple Front (style Vexis, level design, monde vivant)
Copiés depuis `Documents/gmod_triple_front/generator` (projet complet, git, branche master).
Ils dépendent du `kit.py` / `geom.py` de Triple Front (Ctx avec blk/poly/prop/hits/in_clear/gz, building(), oct_prism, frustum, wedge).
- vexis_style.py : MAT_REMAP + PROP_SWAP + LOD (restyler une map existante).
- city_style.py : immeubles accessibles (socle + tour en retrait + couronnement), bataille en ville (barrages, épaves, éboulis).
- rp_style.py : bâtiments et lieux RP posés avec contrôle d'emprise (camp clone, relais, avant-poste droïde, convoi, silos).
- life.py : effets et sons d'ambiance avec plafonds par secteur (mark() puis apply()).
