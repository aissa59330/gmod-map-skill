"""Style « Vexis » pour Triple Front : mêmes textures et mêmes props que rp_cw_arsenal_vexis.

- MAT_REMAP : texture HL2 d'origine -> texture Vexis (appliquée à l'export sur toutes les faces).
- PROP_SWAP : modèle HL2 d'origine -> modèle Vexis (appliqué au placement, donc les contrôles
  « flotte / dans un mur / dans un obstacle » utilisent bien la taille du nouveau modèle).
- LOD : les modèles lourds pour lesquels Vexis a une version allégée (models/vxl/...).
Le contenu (packs extraits + LOD) est embarqué dans le .bsp à la compilation (tools/embed_content.py).
Mettre ENABLED = False pour revenir au style HL2 d'origine.
"""
import json
import os
import re

ENABLED = True
HERE = os.path.dirname(os.path.abspath(__file__))
VEXIS = os.path.join(HERE, os.path.join("..", "generator_tf", "vexis_data"))            # données de Vexis copiées dans le skill (autonome)

# ---------- textures (murs, sols, toits) ----------
MAT_REMAP = {
    # ville : façades et intérieurs -> cité sci-fi
    "plaster/plasterwall030a": "rp_undercity/rp_undercity_metal_wall_17",
    "concrete/concretewall064a": "rp_anaxes/rp_anaxes_metal_dirty2",
    "brick/brickwall031b": "rp_undercity/rp_undercity_metal_wall_13",
    "brick/brickwall045c": "rp_undercity/rp_undercity_metal_wall_22",
    "building_template/building_template003a": "pk02/pk02_wall_big01a",
    "building_template/building_template002a": "pk02/pk02_wall_big01b",
    "concrete/concretewall041a": "rp_undercity/rp_undercity_metal_wall_38",
    "concrete/concretefloor026a": "rp_anaxes/rp_anaxes_concrete_floor11",
    "concrete/concretefloor001a": "rp_anaxes/rp_anaxes_concrete_14",
    "concrete/concretefloor033a": "rp_anaxes/rp_anaxes_concrete_floor11",
    "concrete/concretefloor019a": "rp_anaxes/rp_anaxes_concrete_14",
    "concrete/concretefloor028a": "rp_anaxes/rp_anaxes_concrete_14",
    # route de la ville : même goudron que phoenix_storms/road, mais en vrai matériau de sol (éclairé, sans reflet)
    "phoenix_storms/road": "triple_front/road",
    "stone/stonewall032a": "pk02/pk02_trim_set01a",
    # campagne : fermes et villages -> habitat séparatiste, sol de planète rocheuse
    "wood/woodwall030a": "lordtrilobite/isd_exteriorpanels_dirty",
    "wood/woodwall009a": "lordtrilobite/isd_metal01_dirty",
    "wood/woodfloor005a": "rp_undercity/rp_undercity_metal_floor_14",
    "wood/woodshelf001a": "rp_anaxes/rp_anaxes_metal_floor_7",
    "wood/woodshingles002a": "lordtrilobite/isd_exteriorgreebles_dirty",
    "tile/tileroof003a": "lordtrilobite/isd_exteriorgreebles_dirty",
    "nature/grassfloor002a": "nature/dirtfloor011a",
    "nature/grassfloor003a": "nature/dirtfloor011a",
    "nature/dirtfloor003a": "nature/dirtfloor011a",
    "nature/sandfloor010a": "nature/dirtfloor011a",
    "nature/cliffface001a": "nature/cliffface002a",
    "nature/rockwall010b": "rp_geonosis/rp_geonosis_rock2_red_mumble",
    # base séparatiste
    "metal/citadel_metalwall076a": "old_glory/star_wars_materials/wall4",
    "metal/citadel_metalwall060a": "old_glory/star_wars_materials/wall7",
    "metal/citadel_tilefloor016a": "rp_undercity/rp_undercity_metal_floor_14",
    "metal/metalfloor001a": "lordtrilobite/isd_floor01_dirty",
    "metal/metalcombine001": "lordtrilobite/isd_metal01_dirty",
    "metal/metalcombine002": "pk02/pk02_trim_set01a",
    "metal/metalhull010b": "lordtrilobite/isd_exteriorgreebles_dirty",
}

# ---------- props ----------
N = "models/niksacokica/"
PROP_SWAP = {
    "models/props_c17/lamppost03a_off.mdl": N + "city/city_street_lamp_tall.mdl",
    "models/props_c17/utilitypole01a.mdl": N + "tech/tech_exterior_lightpost.mdl",
    "models/props_foliage/shrub_01a.mdl": "models/fallout_4/landscape/plants/shrubgroupsmall01.mdl",
    "models/props_foliage/tree_deciduous_01a.mdl": "models/props_foliage/tree_dry01_big.mdl",
    "models/props_combine/combine_barricade_short01a.mdl": N + "underworld/und_barricade.mdl",
    "models/props_combine/combine_barricade_med02a.mdl": N + "republic/rep_barricade_metal.mdl",
    "models/props_combine/combine_fence01a.mdl": N + "republic/rep_barricade_metal.mdl",
    "models/props_c17/fence01a.mdl": N + "underworld/und_barricade.mdl",
    "models/props_c17/concrete_barrier001a.mdl": N + "underworld/und_barricade.mdl",
    "models/props_lab/lockers.mdl": N + "republic/rep_console02.mdl",
    "models/props_lab/servers.mdl": N + "republic/rep_console02.mdl",
    "models/props_combine/combine_interface001.mdl": N + "republic/rep_console02.mdl",
    "models/props_lab/generatorconsole.mdl": N + "republic/rep_computer_table.mdl",
    "models/props_debris/concrete_wallpile01a.mdl": N + "containers/con_crate_shipping02_destroyed.mdl",
    "models/props_debris/concrete_debris256pile001a.mdl": N + "caves/caves_medium_boulder_neu_01.mdl",
    "models/props_trainstation/trashcan_indoor001a.mdl": N + "misc/misc_campfire_barrel.mdl",
    "models/props_combine/combine_light001a.mdl": N + "misc/misc_campfire_barrel.mdl",
    "models/props_trainstation/benchoutdoor01a.mdl": N + "city/city_furn_bench_metal.mdl",
    "models/props_wasteland/laundry_dryer001.mdl": N + "tech/tech_mine_barrel.mdl",
    "models/props_c17/furniturestove001a.mdl": N + "republic/rep_crate.mdl",
    "models/props_rooftop/satellitedish02.mdl": N + "tech/tech_canister_fire.mdl",
    "models/props_rooftop/roof_vent001.mdl": N + "containers/con_small_container_pipes_stack.mdl",
    "models/props_rooftop/chimneypipe_cluster02a.mdl": N + "containers/con_tank_toxic_damaged_01.mdl",
    "models/props_rooftop/antennaclusters01a.mdl": N + "tech/tech_missiles_large.mdl",
    "models/props_combine/headcrabcannister01a.mdl": N + "tech/tech_missiles_large.mdl",
    "models/props_combine/combine_mortar01a.mdl": N + "items/banner_separatist.mdl",
    "models/props_wasteland/coolingtank02.mdl": N + "tech/tech_droid_pod.mdl",
    "models/props_wasteland/horizontalcoolingtank04.mdl": N + "tech/tech_huge_generator.mdl",
    "models/props_combine/combine_generator01.mdl": N + "tech/tech_huge_generator.mdl",
    "models/props_canal/generator01.mdl": N + "tech/tech_huge_generator.mdl",
    "models/props_vehicles/generatortrailer01.mdl": N + "construction/construction_storage_compactor_01.mdl",
    "models/props_junk/trashdumpster02.mdl": N + "construction/construction_dumpster_droid.mdl",
    "models/props_wasteland/cargo_container01.mdl": N + "imperial/imp_crate_02_x12.mdl",
    # véhicules civils -> caisses, conteneurs et épaves séparatistes
    "models/props_vehicles/car001b_hatchback.mdl": N + "containers/con_box_crate_06.mdl",
    "models/props_vehicles/car002a.mdl": N + "construction/construction_dumpster_droid.mdl",
    "models/props_vehicles/car003a.mdl": N + "containers/con_box_crate_02.mdl",
    "models/props_vehicles/car004a.mdl": N + "debris/debris_generic_engine_01_env.mdl",
    "models/props_vehicles/car005a.mdl": N + "containers/con_crate_shipping02.mdl",
    "models/props_vehicles/van001a.mdl": N + "imperial/imp_crate_02_x08.mdl",
    "models/props_vehicles/truck001a.mdl": N + "imperial/imp_crate_02_x12.mdl",
    "models/props_vehicles/truck003a.mdl": N + "tech/tech_mining_drill.mdl",
    "models/props_vehicles/tanker001a.mdl": N + "imperial/imp_crate_02_x12.mdl",
    "models/props_vehicles/trailer002a.mdl": N + "imperial/imp_crate_02_x05.mdl",
    "models/props_vehicles/wagon001a.mdl": N + "republic/rep_crate_02_open.mdl",
}

# tailles des modèles Vexis (même fichier que le générateur de Vexis)
VEXIS_BOUNDS = json.load(open(os.path.join(VEXIS, "prop_bounds.json"), encoding="utf-8"))

# modèles qui ont une version LOD allégée (faite pour Vexis) : models/vxl/<nom>.mdl
LOD = set(re.findall(r"^OK (models/\S+\.mdl) :",
                     open(os.path.join(VEXIS, "lod_report.txt"), encoding="utf-8").read(), re.M))


def swap(model):
    return PROP_SWAP.get(model, model) if ENABLED else model


def out_model(model):
    """Modèle écrit dans la map : version LOD si elle existe."""
    if ENABLED and model in LOD:
        return "models/vxl/" + os.path.basename(model)
    return model


def remap_mat(mat):
    return MAT_REMAP.get(mat.lower(), mat) if ENABLED else mat
