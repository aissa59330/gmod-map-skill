"""Bâtiments et points RP ajoutés dans les 3 secteurs (moins de vide, joueurs ralentis, histoire visible).

Tout est posé avec contrôle : emprise libre (ni route, ni obstacle, ni rivière), sol plat sous l'emprise.
Repères RP (camp clone, poste médical, relais radio, avant-poste droïde, convoi détruit) : chacun a un nom
qui apparaît sur le plan et dans la fiche organisateurs.
Perfs : les silos et pylônes pleins sont en brushes monde (ils coupent la visibilité dans les grands espaces
ouverts, donc aident les FPS) ; le reste du décor est en func_detail ; props Vexis en LOD.
"""
from geom import oct_prism, frustum
from kit import RNG, building
import life

N = "models/niksacokica/"
MIL = "concrete/concretewall064a"            # remplacé par le métal Vexis à l'export (vexis_style)
SEP = "metal/citadel_metalwall076a"
SEP_IN = "metal/citadel_metalwall060a"
SEP_FL = "metal/citadel_tilefloor016a"
PLATE = "metal/metalfloor001a"
REP_BAR = N + "republic/rep_barricade_metal.mdl"
DROID_BAR = N + "underworld/und_barricade.mdl"
AMMO = [N + "imperial/imp_crate_02_x04.mdl", N + "imperial/imp_crate_02_x05.mdl", N + "republic/rep_crate.mdl",
        N + "containers/crate_weapon_02.mdl"]
STATS = {"batiments_rp": 0, "points_rp": 0, "silos": 0}


def _snap(v):
    return int(v // 16 * 16)


def free(c, box, margin=192):
    """Emprise libre (avec marge de circulation) et sol plat dessous."""
    x0, y0, x1, y1 = box
    grow = (x0 - margin, y0 - margin, 0, x1 + margin, y1 + margin, 400)
    if c.in_clear(grow) or c.hits(grow):
        return None
    zs = {round(c.gz(x, y, 600)) for x in (x0, (x0 + x1) / 2, x1) for y in (y0, (y0 + y1) / 2, y1)}
    if len(zs) != 1:
        return None
    return zs.pop()


def try_building(c, cx, cy, w, d, floors, fh, ext, inner, floor_mat, roof, doors, **kw):
    box = (_snap(cx - w / 2), _snap(cy - d / 2), _snap(cx + w / 2), _snap(cy + d / 2))
    z = free(c, box)
    if z is None:
        return None
    info = building(c, box[0], box[1], box[2], box[3], z, floors, fh, ext, inner, floor_mat, roof, doors=doors, **kw)
    STATS["batiments_rp"] += 1
    return box


def fill_buildings(c, rect, n, styles, tries=60):
    """Pose jusqu'à n bâtiments dans rect, en petits groupes (un hameau, pas des cubes isolés)."""
    x0, y0, x1, y1 = rect
    done = []
    for _ in range(tries):
        if len(done) >= n:
            break
        if done and RNG.random() < 0.6:            # à côté d'un bâtiment déjà posé : forme un groupe
            b = RNG.choice(done)
            cx = (b[0] + b[2]) / 2 + RNG.choice([-1, 1]) * RNG.uniform(900, 1300)
            cy = (b[1] + b[3]) / 2 + RNG.choice([-1, 1]) * RNG.uniform(0, 700)
        else:
            cx, cy = RNG.uniform(x0, x1), RNG.uniform(y0, y1)
        ext, inner, fl, roof = RNG.choice(styles)
        w, d = RNG.choice([(640, 512), (768, 576), (896, 640), (576, 768)])
        floors = 2 if (w >= 768 and RNG.random() < 0.5) else 1
        doors = (RNG.choice(["y0", "y1"]), RNG.choice(["x0", "x1"]))
        b = try_building(c, cx, cy, w, d, floors, 256 if floors == 2 else 288, ext, inner, fl, roof, doors,
                         roof_access=floors == 2)
        if b:
            done.append(b)
    return done


def silo(c, cx, cy, r, h, mat=SEP):
    """Silo / pylône plein (brushes monde : occulteur) avec couronne à la Vexis."""
    z = free(c, (cx - r, cy - r, cx + r, cy + r), margin=96)
    if z is None:
        return False
    c.poly(oct_prism(cx, cy, r, z, z + h, mat, kind="world"))
    c.poly(oct_prism(cx, cy, r + 48, z + h, z + h + 48, PLATE))
    c.poly(frustum((cx - r, cy - r, z + h + 48, cx + r, cy + r, z + h + 48 + r), r * 0.7, mat))
    STATS["silos"] += 1
    return True


def _ring(c, model, cx, cy, rx, ry, step=210):
    """Périmètre de barricades autour d'un point, avec une entrée de chaque côté x."""
    for x in range(int(cx - rx), int(cx + rx), step):
        for y in (cy - ry, cy + ry):
            c.prop(model, x + step / 2, y, 90 + RNG.uniform(-4, 4))
    for y in range(int(cy - ry + step), int(cy + ry - step), step):
        if abs(y + step / 2 - cy) > 260:          # entrée de 520 au milieu des côtés est et ouest
            for x in (cx - rx, cx + rx):
                c.prop(model, x, y + step / 2, RNG.uniform(-4, 4))


def rep_camp(c, cx, cy, name):
    """Camp clone avancé : préfabriqué de commandement, poste médical, relais radio, réserve de munitions."""
    a = try_building(c, cx - 512, cy, 640, 512, 1, 288, MIL, MIL, "concrete/concretefloor001a", "concrete/concretefloor026a",
                     ("x1",), roof_access=False, name=None)
    b = try_building(c, cx + 512, cy + 128, 512, 384, 1, 288, MIL, MIL, "concrete/concretefloor001a", "concrete/concretefloor026a",
                     ("x0",), roof_access=False, light="230 255 230 160")
    if not a and not b:
        return False
    _ring(c, REP_BAR, cx, cy, 1150, 800)
    c.prop(N + "republic/rep_computer_table.mdl", cx, cy - 300, 0)            # table de briefing
    for dx in (-140, 140):
        c.prop(N + "republic/rep_console02.mdl", cx + dx, cy - 520, 0)        # radio / ordres
        c.prop(N + "republic/rep_lightpole.mdl", cx + dx * 4, cy + 560, 0, solid=0)
    for k in range(4):
        c.prop(AMMO[k % len(AMMO)], cx - 300 + k * 120, cy + 420, RNG.choice([0, 90]))
    c.info[name] = (cx, cy + 950)
    STATS["points_rp"] += 1
    return True


def relay(c, cx, cy, name):
    """Relais de communication : mât, consoles, petit abri (objectif à prendre ou à saboter)."""
    if free(c, (cx - 400, cy - 400, cx + 400, cy + 400), margin=96) is None:
        return False
    z = round(c.gz(cx, cy, 600))
    c.blk((cx - 384, cy - 384, z, cx + 384, cy + 384, z + 16), PLATE, ground=True, obst=False)
    c.poly(oct_prism(cx, cy, 24, z + 16, z + 1100, "metal/metalcombine001"))
    c.poly(oct_prism(cx, cy, 96, z + 1100, z + 1140, PLATE))
    for (dx, yaw) in ((-200, 90), (200, 270)):
        c.prop(N + "republic/rep_console02.mdl", cx + dx, cy, yaw, z=z + 16, check=False)
    c.prop(N + "tech/tech_power_cores_shielded_01.mdl", cx, cy - 250, 0, z=z + 16, check=False)
    life.mark(c, "spark", cx, cy, z + 1080)
    c.info[name] = (cx, cy + 500)
    STATS["points_rp"] += 1
    return True


def droid_post(c, cx, cy, name):
    """Avant-poste droïde : abri séparatiste, barricades droïdes, bannière, capsule de déploiement."""
    a = try_building(c, cx, cy, 640, 512, 1, 288, SEP, SEP_IN, SEP_FL, PLATE, ("x0", "y0"), roof_access=False,
                     light="180 200 255 150")
    if not a:
        return False
    for dy in (-420, -210, 210, 420):
        c.prop(DROID_BAR, cx - 600, cy + dy, 0)
    c.prop(N + "items/banner_separatist.mdl", cx - 420, cy - 360, 270)
    c.prop(N + "items/banner_separatist.mdl", cx - 420, cy + 360, 270)
    c.prop(N + "tech/tech_droid_pod.mdl", cx + 600, cy + 300, 0)
    c.prop(N + "tech/tech_power_cores_shielded_01.mdl", cx + 500, cy - 300, 90)
    life.mark(c, "flicker", cx, cy, 240)
    if name:
        c.info[name] = (cx, cy + 700)
    STATS["points_rp"] += 1
    return True


def convoy(c, x0, x1, y, name):
    """Convoi République détruit sur une piste : carcasses alignées, caisses éventrées autour."""
    n = 0
    x = x0
    while x < x1:
        if c.prop(N + "debris/debris_generic_engine_01_env.mdl", x, y + RNG.uniform(-60, 60), RNG.uniform(-25, 25), road_ok=True):
            n += 1
            life.mark(c, "fire" if n % 2 else "smoke", x, y, 40)
            c.prop(N + "republic/rep_crate_02_broken.mdl", x + RNG.uniform(-200, 200), y + RNG.choice([-260, 260]),
                   RNG.uniform(0, 360), road_ok=True)
        x += RNG.uniform(500, 800)
    if n:
        c.info[name] = ((x0 + x1) / 2, y + 500)
        STATS["points_rp"] += 1
