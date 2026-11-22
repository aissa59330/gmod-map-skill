"""Secteur ville de Triple Front, passe « level design » (style Vexis).

1. Immeubles ACCESSIBLES : chaque immeuble a un rez-de-chaussée praticable (socle à 1 ou 2 étages, en brushes
   monde pour garder l'occultation de la visibilité), puis une tour pleine en retrait (occulteur) et un couronnement
   à la Vexis (champignon, gradins, pyramide). Les petits bâtiments reçoivent auvents, corniches, citernes de toit.
2. La ville RACONTE la bataille : les clones tiennent l'ouest (FOB) et ont repris la ville rue par rue.
   - ligne République : checkpoints en chicane sur les 3 avenues (barricades, murets de plaques, caisses de munitions) ;
   - no man's land au centre : épaves et carcasses sur les avenues, gravats ;
   - ancienne ligne droïde à l'est, devant le quartier détruit : barricades droïdes, bannières, capsules éventrées,
     éboulis qui coupent à moitié les rues transversales.
   Rien n'est posé au hasard : tout est placé aux carrefours, le long des lignes, avec un passage garanti.
Perfs : décor en func_detail (n'alourdit pas la visibilité), props en LOD (vexis_style), pas de nouvelle lumière.
"""
import math

from geom import oct_prism, frustum
from kit import RNG, building, DOOR_H, wedge
import life

TRIM = "pk02/pk02_trim_set01a"
AWN = "lordtrilobite/isd_exteriorgreebles_dirty"
PLATE = "rp_anaxes/rp_anaxes_metal_dirty2"          # murets de plaques (protections improvisées)
RUBBLE = "rp_anaxes/rp_anaxes_concrete_14"
TANK = "lordtrilobite/isd_metal01_dirty"
N = "models/niksacokica/"
REP_BAR = N + "republic/rep_barricade_metal.mdl"
DROID_BAR = N + "underworld/und_barricade.mdl"
AMMO = [N + "imperial/imp_crate_02_x04.mdl", N + "imperial/imp_crate_02_x05.mdl", N + "containers/crate_weapon_02.mdl",
        N + "republic/rep_crate.mdl"]
WRECKS = [N + "debris/debris_generic_engine_01_env.mdl", N + "containers/con_crate_shipping02_destroyed.mdl",
          N + "construction/construction_dumpster_droid.mdl"]
DROID_JUNK = [N + "items/banner_separatist.mdl", N + "tech/tech_droid_pod.mdl", N + "containers/con_tank_toxic_damaged_01.mdl",
              N + "republic/rep_crate_02_broken.mdl"]
STATS = {"checkpoints": 0, "epaves": 0, "eboulis": 0, "couronnes": 0, "socles": 0}


# ------------------------------------------------------------------ architecture
def _mid(a, b):
    return int(((a + b) / 2) // 16 * 16)


def cornice(c, x0, y0, x1, y1, z, h=32, out=16):
    """Bandeau saillant autour d'un volume : casse la façade lisse, marque l'étage."""
    for b in ((x0 - out, y0 - out, z, x1 + out, y0, z + h), (x0 - out, y1, z, x1 + out, y1 + out, z + h),
              (x0 - out, y0, z, x0, y1, z + h), (x1, y0, z, x1 + out, y1, z + h)):
        c.blk(b, TRIM, obst=False)


def crown(c, x0, y0, x1, y1, z, ext):
    """Couronnement de tour, inspiré de Vexis (pas de toit plat partout)."""
    w, d = x1 - x0, y1 - y0
    cx, cy = _mid(x0, x1), _mid(y0, y1)
    r = min(w, d) / 2
    kind = RNG.choice(["champignon", "gradins", "pyramide", "antennes"])
    if kind == "champignon" and r >= 160:          # tour champignon : disque large + fût + mât
        c.poly(oct_prism(cx, cy, r * 0.55, z, z + 160, TANK))
        c.poly(oct_prism(cx, cy, r + 48, z + 160, z + 224, ext))
        c.prop("models/props_rooftop/antennaclusters01a.mdl", cx, cy, 0, z=z + 224, solid=0, check=False)
    elif kind == "gradins" and min(w, d) >= 384:   # retraits successifs
        k = 0.22
        b1 = (x0 + w * k, y0 + d * k, z, x1 - w * k, y1 - d * k, z + RNG.choice([192, 256, 320]))
        b1 = tuple(int(v // 16 * 16) for v in b1)
        c.blk(b1, ext, obst=False)
    elif kind == "pyramide":
        c.poly(frustum((x0 + 32, y0 + 32, z, x1 - 32, y1 - 32, z + int(min(w, d) * 0.35 // 16 * 16 + 64)),
                       min(w, d) // 3, AWN))
    else:                                          # toit technique : équipements (props LOD, sans collision)
        for _ in range(RNG.randint(2, 3)):
            m = RNG.choice(["models/props_rooftop/roof_vent001.mdl", "models/props_rooftop/chimneypipe_cluster02a.mdl",
                            "models/props_rooftop/antennaclusters01a.mdl", "models/props_rooftop/satellitedish02.mdl"])
            c.prop(m, RNG.uniform(x0 + 96, x1 - 96), RNG.uniform(y0 + 96, y1 - 96), RNG.choice([0, 90, 180]), z=z, solid=0)
    STATS["couronnes"] += 1


def awnings(c, x0, y0, x1, y1, doors):
    """Auvent au-dessus de chaque porte (repère visuel des entrées, abri)."""
    z = 16 + 16 + DOOR_H + 24
    for s in doors:
        if s in ("y0", "y1"):
            m = _mid(x0, x1)
            yy = (y0 - 96, y0) if s == "y0" else (y1, y1 + 96)
            c.blk((m - 160, yy[0], z, m + 160, yy[1], z + 16), AWN, obst=False)
        else:
            m = _mid(y0, y1)
            xx = (x0 - 96, x0) if s == "x0" else (x1, x1 + 96)
            c.blk((xx[0], m - 160, z, xx[1], m + 160, z + 16), AWN, obst=False)


def podium_tower(c, x0, y0, x1, y1, h, ext, inner, floor_mat, roof, doors):
    """Immeuble praticable : socle creux (1-2 niveaux) + tour pleine en retrait + couronnement."""
    wx, wy = x1 - x0, y1 - y0
    big = wx >= 896 and wy >= 576
    floors = 2 if big else 1
    fh = 256 if big else 288
    # socle en brushes monde : il garde l'occultation que faisait l'ancienne tour pleine
    info = building(c, x0, y0, x1, y1, 16, floors, fh, ext, inner, floor_mat, roof, doors=doors,
                    kind="world", roof_access=big, parapet=big, windows=big)
    top = info["top"]
    awnings(c, x0, y0, x1, y1, doors)
    up = max(384, int((h - top) // 16 * 16))
    if big:                                        # tour en retrait : terrasse praticable devant, trémie d'escalier libre
        ins = RNG.choice([96, 128, 192])
        tb = (x0 + ins, y0 + ins, x1 - ins, y1 - 32 - 160 - 192)
    else:                                          # petit immeuble : la tour repose sur toute l'emprise
        tb = (x0, y0, x1, y1)
    if tb[2] - tb[0] >= 256 and tb[3] - tb[1] >= 256:
        c.blk((tb[0], tb[1], top, tb[2], tb[3], top + up), ext, "world", top=roof)
        crown(c, tb[0], tb[1], tb[2], tb[3], top + up, ext)
    STATS["socles"] += 1
    return info


def dress_building(c, x0, y0, x1, y1, info, doors, ext):
    """Petits bâtiments : auvents, corniche, citerne ou édicule sur le toit (silhouette moins cubique)."""
    awnings(c, x0, y0, x1, y1, doors)
    top = info["top"]
    roll = RNG.random()
    if roll < 0.4 and min(x1 - x0, y1 - y0) >= 512:   # citerne ronde, côté sud (loin de la trémie nord)
        cx, cy = _mid(x0 + 128, x0 + 384), y0 + 192
        c.poly(oct_prism(cx, cy, 96, top, top + 192, TANK))
        c.poly(oct_prism(cx, cy, 112, top + 192, top + 224, TRIM))
    elif roll < 0.7 and (x1 - x0) >= 640:               # édicule plein sur le toit (2e volume)
        c.blk((x1 - 320, y0 + 64, top, x1 - 64, y0 + 320, top + 160), ext, obst=False)


# ------------------------------------------------------------------ la bataille
def _bar_line(c, model, x, y0, y1, yaw, step=200):
    n = 0
    y = y0 + step / 2
    while y < y1:
        if c.prop(model, x, y, yaw + RNG.uniform(-4, 4), road_ok=True):
            n += 1
        y += step
    return n


def plate_wall(c, x0, y0, x1, y1, h=64):
    """Muret improvisé en plaques de blindage (couvert à hauteur d'homme accroupi)."""
    c.blk((x0, y0, 0, x1, y1, h), PLATE)


def checkpoint(c, x, ay0, ay1, face, faction):
    """Barrage en chicane en travers d'une avenue (bande y = ay0..ay1) à l'abscisse x.
    face = +1 : tourné vers l'est (défenseurs à l'ouest) ; -1 : tourné vers l'ouest.
    Deux demi-lignes décalées de 320 : on passe en zigzag, jamais en ligne droite (passage >= 256)."""
    mid = _mid(ay0, ay1)
    bar = REP_BAR if faction == "rep" else DROID_BAR
    _bar_line(c, bar, x, ay0 + 32, mid - 128, 0)
    _bar_line(c, bar, x - face * 320, mid + 128, ay1 - 32, 0)
    # murets en L côté défenseurs, contre les trottoirs
    back = x - face * 160
    plate_wall(c, min(back, back - face * 32), ay0 + 16, max(back, back - face * 32), ay0 + 208)
    plate_wall(c, min(back, back - face * 32) - face * 320, ay1 - 208, max(back, back - face * 32) - face * 320, ay1 - 16)
    # réserve derrière la ligne
    if faction == "rep":
        for k in range(3):
            c.prop(RNG.choice(AMMO), x - face * (448 + 96 * k), ay0 + 160 + 64 * k, RNG.choice([0, 90]), road_ok=True)
    else:
        c.prop(N + "items/banner_separatist.mdl", x - face * 96, ay0 + 96, 90 if face > 0 else 270, road_ok=True)
        c.prop(N + "tech/tech_droid_pod.mdl", x - face * 640, mid, 0, road_ok=True)
    life.mark(c, "flicker" if faction == "rep" else "spark", x - face * 200, mid, 150)
    STATS["checkpoints"] += 1


def wreck_field(c, xa, xb, avenues):
    """No man's land : quelques épaves et carcasses le long des avenues (pas au milieu de la voie)."""
    for (ay0, ay1) in avenues:
        x = xa + RNG.uniform(200, 500)
        while x < xb - 200:
            side = RNG.choice([ay0 + 160, ay1 - 160])
            if c.prop(RNG.choice(WRECKS), x, side, RNG.uniform(0, 360), road_ok=True):
                STATS["epaves"] += 1
                life.mark(c, "fire", x, side, 40)
            x += RNG.uniform(900, 1500)


def rubble(c, sx0, sx1, y0, y1):
    """Éboulis d'immeuble effondré : coupe la moitié d'une rue transversale, franchissable (pente douce)."""
    half = RNG.choice([0, 1])
    a, b = (sx0, _mid(sx0, sx1)) if half == 0 else (_mid(sx0, sx1), sx1)
    m = _mid(y0, y1)
    h = RNG.choice([64, 80, 96])
    c.poly(wedge(a, y0, b, m, 0, h, "y1", RUBBLE))
    c.poly(wedge(a, m, b, y1, 0, h, "y0", RUBBLE))
    c.prop(RNG.choice(["models/props_debris/concrete_wallpile01a.mdl", "models/props_debris/concrete_debris256pile001a.mdl"]),
           _mid(a, b), m, RNG.uniform(0, 360), road_ok=True, check=False, z=h - 8)
    life.mark(c, "smoke", _mid(a, b), m, h)
    STATS["eboulis"] += 1


def battle(c, streets_x, avenues, plaza_a, plaza_b, ruin_x0):
    """Front de la ville : ligne République (ouest), no man's land (centre), ancienne ligne droïde (est)."""
    rep_streets = [s for s in streets_x if s[1] <= plaza_a][-3:]          # 3 dernières rues avant la place
    for k, (ay0, ay1) in enumerate(avenues):
        a, b = rep_streets[k % len(rep_streets)]
        checkpoint(c, b + 256, ay0, ay1, +1, "rep")
    droid_street = [s for s in streets_x if s[1] <= ruin_x0][-1]
    for (ay0, ay1) in avenues:
        checkpoint(c, droid_street[0] - 256, ay0, ay1, -1, "cis")
    wreck_field(c, plaza_b, droid_street[0] - 900, avenues)
    # éboulis dans les rues transversales du quartier détruit (entre deux avenues)
    bands = [(-6400, -4480), (-3456, -576), (576, 3456), (4480, 6400)]
    for (sx0, sx1) in [s for s in streets_x if s[0] >= ruin_x0 - 512][:3]:
        for (y0, y1) in RNG.sample(bands, 2):
            rubble(c, sx0, sx1, y0 + 256, y0 + 256 + 768)
