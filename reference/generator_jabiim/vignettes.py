"""Petites scènes détaillées (« vignettes ») façon clazfort : chaque endroit raconte quelque chose.

Inspiration (analyse de rp_clazfort et de Vexis) : des lieux denses en petits objets (lampes, clôtures, caisses, mobilier,
tuyaux, débris), des bosquets groupés plutôt que des arbres isolés, des pistes avec lampadaires, des intérieurs meublés.
Tout vient du catalogue de Vexis (props statiques, avec LOD quand ils existent). Les murets de sacs / terre sont de
petits brushes func_detail (très peu de sommets).

Utilisation : scatter_scenes(v, ...) place ~70 scènes variées (thème selon la région), tracks(v) trace les pistes,
groves(v) les bosquets, furnish(v, ...) meuble un bâtiment, street(v, ...) habille une rue.
"""
import math
import random

import shapes as S
import vx as VX
from vx import M

R = random.Random(2203)
# refusés en prop_static par vbsp (pas de $staticprop ou prop_data « dynamique seulement »)
NOT_STATIC = {"wood_fence02a", "bluebarrel001", "furnitureshelf001a", "shelfunit01a", "streetsign004e", "pushcart01a", "hyperfuelbarrel01"}
IDX = {}
for _k, _b in VX.BOUNDS.items():
    _n = _k.split("/")[-1][:-4]
    if _b.get("static") is not False and _n not in IDX and _n not in NOT_STATIC:
        IDX[_n] = _k
EARTH = "nature/dirtfloor011a"
STATS = {"scenes": 0, "themes": {}, "pistes": 0, "lampadaires": 0, "bosquets": 0, "meubles": 0}


def md(name):
    return name if name.startswith("models/") else IDX[name]


class Scene:
    """Repère local d'une scène : (lx, ly) tournés de yaw puis posés en (x, y)."""

    def __init__(self, v, x, y, yaw, why):
        self.v, self.x, self.y, self.yaw, self.why = v, x, y, yaw, why
        self.c, self.s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def w(self, lx, ly):
        return self.x + lx * self.c - ly * self.s, self.y + lx * self.s + ly * self.c

    def p(self, name, lx=0, ly=0, lyaw=0, **kw):
        x, y = self.w(lx, ly)
        kw.setdefault("why", self.why)
        self.v.prop(md(name), x, y, (self.yaw + lyaw) % 360, **kw)

    def many(self, names, n, r, **kw):
        for _ in range(n):
            a, d = R.uniform(0, 2 * math.pi), r * math.sqrt(R.random())
            self.p(R.choice(names), d * math.cos(a), d * math.sin(a), R.uniform(0, 360), **kw)

    def wall(self, lx, ly, length, lyaw=0, h=64, mat=EARTH, thick=56):
        """Muret de sacs / terre (petit brush incliné en tronc de pyramide)."""
        x, y = self.w(lx, ly)
        z = self.v.gz(x, y) - 16
        self.v.add(S.obox(x, y, z, length, thick, h + 16, self.yaw + lyaw, mat, "detail"), obst=True)

    def fx(self, kind, lx, ly, dz, **kv):
        x, y = self.w(lx, ly)
        self.v.fx.append((kind, (x, y, self.v.gz(x, y) + dz), kv))


CRATES = ["con_box_crate_02", "con_box_crate_03", "con_box_crate_06", "box_crate"]
DEBRIS = ["debris_droid_parts_astromech_body", "debris_droid_parts_astromech_head", "con_crate_04_broken"]


# ------------------------------------------------------------------ les scènes (environ 600 x 600 chacune)
def feu_de_camp(sc):
    sc.p("misc_campfire_barrel", 0, 0)
    sc.fx("fire", 0, 0, 30, size=48)
    for a in (20, 140, 260):
        sc.p(R.choice(["con_box_crate_02", "rep_peasant_chair"]), 150 * math.cos(math.radians(a)), 150 * math.sin(math.radians(a)), a + 180)
    sc.p("rep_noble_tent", 0, 380, 180)
    sc.p("con_box_crate_06", 260, -200, 15); sc.p("con_box_crate_03", 300, -120, 70)
    sc.p("combine_light001a", -320, 180, 0)


def nid_mitrailleuse(sc):
    for (lx, ly, a, L) in ((0, 260, 0, 520), (-250, 40, 90, 400), (250, 40, 90, 400)):
        sc.wall(lx, ly, L, a)
    sc.p("turret_neu_tracking", 0, 120, 90)
    sc.many(["con_box_crate_02", "con_box_crate_03"], 4, 160)
    sc.p("light_spotlight01_lamp", -160, 200, 90)


def poste_controle(sc):
    for k, ly in enumerate((-260, 0, 260)):
        sc.p("rep_barricade_metal", (-120 if k % 2 else 120), ly, 90)
    sc.p("lamppost03a_off", -320, -320, 90)
    sc.p("flag", 320, -320, 0)
    sc.p("rep_console02", 300, 120, 270)
    sc.p("city_firebarrel", -300, 260, 0)
    sc.fx("fire", -300, 260, 26, size=36)


def depot(sc):
    for k in range(3):
        sc.p("rep_pallet_02", -200 + k * 130, -180, 0)
        sc.p(R.choice(CRATES), -200 + k * 130, -180, R.uniform(-10, 10), z=None)
    sc.p("cargo_container01", 220, 120, 90)
    sc.p("generator01", -260, 200, 0)
    sc.p("light_spotlight01_lamp", -60, 260, 270)
    sc.many(CRATES, 5, 260)


def epave_speeder(sc):
    sc.p("veh_neu_speeder_02_wreckage", 0, 0, 25)
    sc.many(["veh_neu_speeder_02_debris"] + DEBRIS, 6, 300)
    sc.fx("smoke", 20, 0, 40, rate=5, size=260, color="55 52 50")


def droides_detruits(sc):
    sc.p("debris_droid_parts_hk51_group01", 0, 0, R.uniform(0, 360))
    sc.many(DEBRIS + ["debris_droid_parts_astromech_leg"], 9, 340)
    sc.wall(0, -260, 420, 0, h=48)


def capsule(sc):
    sc.p("tech_imperial_pod_01", 0, 0, 30, sink=40)
    sc.p("tech_imperial_pod_door_open", 220, 90, 70)
    sc.many(DEBRIS, 5, 320)
    sc.fx("smoke", 0, 0, 80, rate=4, size=320, color="60 58 56")


def camp_medical(sc):
    sc.p("rep_noble_tent", 0, 0, 0)
    sc.p("imp_medical_bed", -260, -260, 90); sc.p("imp_medical_bed", 0, -280, 90)
    sc.p("tech_medical_light_longpole", -130, -360, 0)
    sc.p("bacta_tank", 300, -120, 0)
    sc.many(["con_box_crate_03", "con_box_crate_02"], 3, 200)


def relais(sc):
    sc.p("antennaclusters01a", 0, 0, 0)
    sc.p("satellitedish02", 200, 120, 200); sc.p("satellitedish02", -180, 160, 140)
    sc.p("generator_portable", 120, -160, 0); sc.p("rep_console02", -140, -150, 180)
    sc.wall(0, 300, 480, 0, h=48)


def atelier(sc):
    sc.p("tech_city_workbench", 0, 0, 0)
    sc.p("tech_city_workbench_device", -40, 10, 0)
    sc.p("lockers", -260, 140, 270); sc.p("tech_armory_locker", -260, 30, 270)
    sc.p("generatortrailer01", 260, 200, 90)
    sc.many(CRATES, 4, 300)


def mine_artisanale(sc):
    sc.v.add(S.cone(sc.x, sc.y, 300, 60, sc.v.gz(sc.x, sc.y) - 24, sc.v.gz(sc.x, sc.y) + 180, EARTH, "detail", 9))
    sc.p("tech_mine_barrel", 360, 0, 0); sc.p("tech_mine_barrel", 420, 90, 0)
    sc.p("con_box_crate_02", 300, -220, 30)
    sc.p("tech_mine_canister", -360, 160, 0) if "tech_mine_canister" in IDX else None
    sc.p("construction_crane_clamp", -300, -200, 0) if "construction_crane_clamp" in IDX else None


def statue_ruine(sc):
    sc.p("ruins_jedi_statue_destroyed", 0, 0, R.uniform(0, 360))
    sc.p("ruins_jedi_statue_parts_head", 360, 120, 40); sc.p("ruins_jedi_statue_parts_arm_01", -320, -200, 200)
    sc.many(["rockcliff_cluster03a"], 2, 420, sink=30)


def canon_abandonne(sc):
    sc.p("turbolaser_barrel_static", 0, 0, R.uniform(0, 360), sink=20)
    sc.p("concrete_debris256pile001a", 300, 100, 0)
    sc.many(DEBRIS, 4, 320)


def pods_droides(sc):
    for (lx, ly) in ((0, 0), (300, 120), (-260, 200)):
        sc.p("tech_droid_pod_main", lx, ly, R.uniform(0, 360), sink=30)
    sc.many(DEBRIS, 4, 360)
    sc.fx("smoke", 0, 0, 60, rate=4, size=240, color="60 58 56")


def cuves(sc):
    sc.p("tech_kolto_tank_lg", 0, 0, 0)
    sc.p("horizontalcoolingtank04", 0, 300, 0)
    sc.p("pipe_large_512", 260, 120, 90)
    sc.p("con_toxicwaste_barrel", -240, -200, 0); sc.p("tech_mine_barrel", -200, -260, 0)


def caserne_campagne(sc):
    sc.p("rep_noble_tent", 0, 0, 90)
    sc.p("rep_bunk_beds_x4", -300, 0, 90)
    sc.p("tech_armory_locker", 260, -160, 180); sc.p("lockers", 260, -60, 180)
    sc.p("city_firebarrel", 220, 260, 0)


def poste_commandement(sc):
    for (lx, ly, a, L) in ((0, 340, 0, 640), (0, -340, 0, 640), (-340, 0, 90, 560)):
        sc.wall(lx, ly, L, a, h=56)
    sc.p("tech_holotable_01", 0, 0, 0)
    sc.p("rep_console02", -180, 160, 0); sc.p("rep_hangar_console", 160, 160, 0)
    sc.p("combine_light001a", 220, -220, 0)
    sc.p("flag", -260, -240, 0)


def milice(sc):
    sc.p("rep_barricade_metal", 0, -300, 0); sc.p("rep_barricade_metal", 230, -260, 30)
    sc.p("banner_separatist", -260, 0, 90)
    sc.p("rep_peasant_table", 0, 60, 0); sc.p("rep_peasant_chair", 0, 160, 180); sc.p("rep_peasant_chair", 0, -40, 0)
    sc.p("city_firebarrel", 260, 160, 0)
    sc.fx("fire", 260, 160, 26, size=36)


def marche(sc):
    sc.p("market_banner_canopy_01", 0, 0, 0); sc.p("market_banner_canopy_02", 0, 360, 0)
    sc.p("rep_peasant_table", 60, 0, 90); sc.p("rep_peasant_table", 60, 360, 90)
    sc.many(CRATES + ["con_box_crate_02"], 5, 300)


def generateur(sc):
    sc.p("tech_huge_generator", 0, 0, 0)
    sc.p("generatorconsole", 220, 0, 270) if "generatorconsole" in IDX else None
    sc.wall(0, -260, 420, 0, h=48)
    sc.p("combine_light001a", -220, 200, 0)


def drop(sc):
    sc.p("tech_gsi_drop_box", 0, 0, 0); sc.p("tech_gsi_drop_box", 80, 40, 30)
    sc.many(CRATES, 6, 260)
    sc.p("light_spotlight01_lamp", -200, 0, 0)


def memorial(sc):
    sc.p("city_statue_jedi", 0, 0, 180)
    for k in range(6):
        sc.p("flag", -300 + k * 120, -260, 0)
    sc.many(["shrubgroupsmall01"], 3, 300)


THEMES = {
    "marais": [feu_de_camp, nid_mitrailleuse, epave_speeder, droides_detruits, capsule, camp_medical, poste_commandement,
               caserne_campagne, memorial, drop, statue_ruine, canon_abandonne],
    "centre": [poste_controle, depot, nid_mitrailleuse, generateur, relais, epave_speeder, pods_droides, caserne_campagne, drop,
               milice],
    "hauts": [mine_artisanale, relais, atelier, pods_droides, cuves, canon_abandonne, droides_detruits, depot, statue_ruine,
              generateur, capsule],
    "ville": [marche, milice, depot, poste_controle, atelier, feu_de_camp],
}


def scatter_scenes(v, rect, region_of, in_zone, min_d=1400, n_max=90):
    """Échantillonnage de Poisson : une scène tous les ~1400, jamais deux fois le même thème de suite dans une région."""
    x0, y0, x1, y1 = rect
    pts = []
    bags = {k: [] for k in THEMES}
    for _ in range(4000):
        if len(pts) >= n_max:
            break
        x, y = R.uniform(x0, x1), R.uniform(y0, y1)
        if in_zone(x, y) or any((x - a) ** 2 + (y - b) ** 2 < min_d * min_d for a, b in pts):
            continue
        reg = region_of(x, y)
        if reg is None:
            continue
        if v.t.slope(x, y) > 0.28:
            continue
        if not bags[reg]:
            bags[reg] = THEMES[reg][:]
            R.shuffle(bags[reg])
        fn = bags[reg].pop()
        z = max(v.gz(x, y), 10)
        v.t.flat_disc(x, y, 420, z, 380)
        sc = Scene(v, x, y, R.uniform(0, 360), "scene")
        fn(sc)
        v.zones.append((x - 520, y - 520, x + 520, y + 520, "scene"))
        v.rects.append((x - 420, y - 420, x + 420, y + 420, "scene"))
        pts.append((x, y))
        STATS["scenes"] += 1
        STATS["themes"][fn.__name__] = STATS["themes"].get(fn.__name__, 0) + 1
    return pts


# ------------------------------------------------------------------ pistes et lampadaires
def tracks(v, lines, half=224, lamp_every=1100):
    """Pistes de terre (relief aplani en travers + texture de terre, recette Vexis) bordées de lampadaires."""
    for pts in lines:
        v.t.track(pts, half)
        STATS["pistes"] += 1
        side = 1
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / L, (by - ay) / L
            d = lamp_every / 2
            while d < L:
                x, y = ax + ux * d - uy * (half + 90) * side, ay + uy * d + ux * (half + 90) * side
                v.prop(md("lamppost03a_off"), x, y, math.degrees(math.atan2(uy, ux)) + (90 if side > 0 else -90), why="lampadaire")
                STATS["lampadaires"] += 1
                side = -side
                d += lamp_every


# ------------------------------------------------------------------ bosquets
def groves(v, rect, in_zone, n=40, wet=None):
    x0, y0, x1, y1 = rect
    trees = ["tree_cliff_01a", "tree_cliff_02a", "oak_tree01", "tree_deciduous_01a"]
    dead = ["tree_dry01_big", "tree_cliff_02a"]
    shrubs = ["shrubgrouplarge04", "shrubgroupmedium02", "shrubgroupsmall01"]
    done = 0
    for _ in range(n * 10):
        if done >= n:
            break
        cx, cy = R.uniform(x0, x1), R.uniform(y0, y1)
        if in_zone(cx, cy):
            continue
        swamp = wet(cx, cy) if wet else False
        r = R.uniform(350, 750)
        for _ in range(R.randint(8, 18)):
            a, d = R.uniform(0, 2 * math.pi), r * math.sqrt(R.random())
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if in_zone(x, y):
                continue
            pool = (dead if swamp else trees) if R.random() < 0.6 else shrubs
            v.prop(md(R.choice(pool)), x, y, R.uniform(0, 360), why="bosquet", sink=8)
        done += 1
    STATS["bosquets"] += done


# ------------------------------------------------------------------ intérieurs et rues (Choal)
INTERIOR = [["rep_bunk_beds", "lockers", "rep_peasant_table", "rep_peasant_chair"],
            ["rep_computer_table", "rep_console02", "tech_armory_locker", "chair01"],
            ["con_box_crate_02", "con_box_crate_03", "lockers", "rep_pallet_02"],
            ["rep_peasant_table", "rep_peasant_chair", "rep_peasant_chair", "tech_armory_locker"],
            ["imp_computer_cubicle", "desk_reception", "chair01", "lockers"]]


def furnish(v, box, levels, n_per=3):
    """Meuble chaque niveau d'un bâtiment (kit.building : levels = hauteurs des planchers, dernier = toit)."""
    x0, y0, x1, y1 = box
    kit = R.choice(INTERIOR)
    for z in levels[:-1]:
        for _ in range(n_per):
            x, y = R.uniform(x0 + 96, x1 - 96), R.uniform(y0 + 96, y1 - 96)
            v.prop(md(R.choice(kit)), x, y, R.choice([0, 90, 180, 270]), z=z, why="meuble")
            STATS["meubles"] += 1


def street(v, x0, y0, x1, y1, every=900):
    """Rue : lampadaires d'un côté, de temps en temps un brasero, des caisses, un auvent de marché."""
    along_x = (x1 - x0) > (y1 - y0)
    L = (x1 - x0) if along_x else (y1 - y0)
    d = every / 2
    while d < L:
        if along_x:
            x, y, yaw = x0 + d, y1 - 40, 270
        else:
            x, y, yaw = x1 - 40, y0 + d, 180
        v.prop(md("city_street_lamp"), x, y, yaw, why="rue")
        r = R.random()
        ox, oy = (x, y0 + 60) if along_x else (x0 + 60, y)
        if r < 0.25:
            v.prop(md("city_firebarrel"), ox, oy, 0, why="rue")
        elif r < 0.5:
            v.prop(md(R.choice(CRATES)), ox, oy, R.uniform(0, 360), why="rue")
        elif r < 0.62:
            v.prop(md("market_banner_canopy_01"), ox, oy, 90 if along_x else 0, why="rue")
        d += every


# ------------------------------------------------------------------ scènes avec de VRAIS bâtiments (variété)
PF = "models/lordtrilobite/starwars/props/imp_prefabbase_"
PF_ROOMS = ["roombarracks", "roombrig01", "roomcommand01", "roomcommand02", "roomoffice01", "roomempty01", "roomempty05"]
PF_ALL = [PF + n + ".mdl" for n in PF_ROOMS + ["roomempty06", "end02", "straight01", "straight04_comms", "straight07_window", "l01", "t01"]]


def _flat(sc, r):
    z = max(sc.v.gz(sc.x, sc.y), 12)
    sc.v.t.flat_disc(sc.x, sc.y, r, z, 500)
    return z


def hameau(sc):
    """Hameau jabiimi : 3 à 4 cases rondes au toit conique, brasero, caisses, linge (bannière), clôture."""
    from vx import round_hall
    _flat(sc, 760)
    n = R.choice([3, 4])
    for k in range(n):
        a = math.radians(k * 360 / n + R.uniform(-15, 15))
        x, y = sc.x + 430 * math.cos(a), sc.y + 430 * math.sin(a)
        door = (math.degrees(a) + 180) % 360
        round_hall(sc.v, x, y, R.choice([224, 256, 288]), sc.v.gz(sc.x, sc.y), 224, doors=(door,), roof="cone", wall=M["dirty"],
                   roof_mat=M["hull"], light="255 190 130 120", segs=8, windows=False)
    sc.p("misc_campfire_barrel", 0, 0)
    sc.fx("fire", 0, 0, 30, size=44)
    sc.many(CRATES + ["rep_peasant_table"], 3, 160)
    sc.p("fence03a", 0, 720, 0); sc.p("fence03a", 90, 720, 0)


def poste_prefab(sc):
    """Avant-poste en modules préfabriqués (2 ou 3 salles visitables), barricades, drapeau, générateur."""
    _flat(sc, 820)
    rooms = R.sample(PF_ROOMS, R.choice([2, 3]))
    for k, rm in enumerate(rooms):
        sc.p(PF + rm + ".mdl", (k - (len(rooms) - 1) / 2) * 560, 0, R.choice([0, 180]), why="prefab")
    sc.p("rep_barricade_metal", -300, -520, 0); sc.p("rep_barricade_metal", 300, -520, 0)
    sc.p("generator01", 0, 520, 0)
    sc.p("flag", -620, -380, 0)
    sc.p("combine_light001a", 620, -380, 0)


def caserne_prefab(sc):
    """Caserne préfabriquée en L : salles + couloir, lampes, caisses de munitions."""
    _flat(sc, 820)
    sc.p(PF + "roombarracks.mdl", 0, 0, 0, why="prefab")
    sc.p(PF + "roomempty06.mdl", 0, 560, 90, why="prefab")
    sc.many(CRATES, 5, 300)
    sc.p("light_spotlight01_lamp", -400, -400, 45)


def entrepot(sc):
    """Entrepôt voûté (hangar Vexis) avec conteneurs et palettes devant."""
    from vx import vault_hall
    z = _flat(sc, 900)
    vault_hall(sc.v, sc.x, sc.y, z, 960, 576, 224, 192, sc.yaw, mat=M["wall3"], side_doors=False)
    for k in range(3):
        sc.p(R.choice(["cargo_container01", "rep_pallet_02"]), -300 + k * 300, 560, 0)
    sc.many(CRATES, 4, 260)


for _reg, _extra in (("marais", [hameau, poste_prefab, caserne_prefab]), ("centre", [hameau, poste_prefab, entrepot, caserne_prefab]),
                     ("hauts", [poste_prefab, entrepot, caserne_prefab, hameau])):
    THEMES[_reg] = THEMES[_reg] + _extra * 2          # les bâtiments reviennent plus souvent que les tas d'objets
