-- Contrôle des trous de collision (outil de dev, jamais publié) : rayons verticaux sur toute la zone jouable.
-- Un rayon qui descend sous le plancher du monde (ou ne touche rien) = un joueur pourrait tomber sous la map.
if game.GetMap() ~= "rp_cw_battle_of_jabiim" then return end
local PX, STEP, FLOOR = 13800, 64, -1600
local function run()
    file.CreateDir("jb_check")
    local out, n, bad = {}, 0, 0
    for x = -PX, PX, STEP do
        for y = -PX, PX, STEP do
            local tr = util.TraceLine({start = Vector(x, y, 4000), endpos = Vector(x, y, FLOOR - 200), mask = MASK_PLAYERSOLID})
            n = n + 1
            if (not tr.Hit) or tr.HitPos.z < FLOOR + 8 or tr.HitSky then
                bad = bad + 1
                out[#out + 1] = string.format("%d %d %.0f %s", x, y, tr.HitPos.z, tr.HitTexture or "?")
            else
                -- sous le sol trouvé : y a-t-il un vide traversable (sol trop fin, joueur qui passe à travers) ?
                local tr2 = util.TraceHull({start = tr.HitPos + Vector(0, 0, 40), endpos = tr.HitPos - Vector(0, 0, 40),
                    mins = Vector(-16, -16, 0), maxs = Vector(16, 16, 8), mask = MASK_PLAYERSOLID})
                if not tr2.Hit then
                    -- confirmation : un volume de joueur lâché depuis le ciel passe-t-il SOUS le sol ?
                    local tr3 = util.TraceHull({start = Vector(x, y, 4000), endpos = Vector(x, y, FLOOR - 200),
                        mins = Vector(-16, -16, 0), maxs = Vector(16, 16, 72), mask = MASK_PLAYERSOLID})
                    if tr3.HitPos.z < tr.HitPos.z - 48 then
                        bad = bad + 1
                        out[#out + 1] = string.format("%d %d %.0f CHUTE_%.0f", x, y, tr.HitPos.z, tr3.HitPos.z)
                    end
                end
            end
        end
    end
    -- cavernes et galeries (monde décalé à CAVE_DZ = -3840) : rayons depuis l'air des cavités vers le bas
    local CZ, nc, badc = -3840, 0, 0
    for x = 7168 + 32, 15872, STEP do        -- décalé de 32 : jamais pile sur un plan de mur
        for y = -12288 + 32, 12288, STEP do
            for _, zs in ipairs({300, 900}) do
                local st = Vector(x, y, CZ + zs)
                if bit.band(util.PointContents(st), CONTENTS_SOLID) == 0 then
                    local trc = util.TraceHull({start = st, endpos = Vector(x, y, CZ - 900), mins = Vector(-16, -16, 0),
                        maxs = Vector(16, 16, 8), mask = MASK_PLAYERSOLID})
                    nc = nc + 1
                    if (not trc.Hit) or trc.HitPos.z < CZ - 600 then
                        badc = badc + 1
                        out[#out + 1] = string.format("%d %d %.0f CAVERNE_CHUTE", x, y, trc.HitPos.z)
                    end
                    break
                end
            end
        end
    end
    file.Write("jb_check/result.txt", "rayons " .. n .. " ; trous " .. bad .. " ; cavernes " .. nc .. " rayons, " .. badc .. " chutes\n" ..
        table.concat(out, "\n"))
    timer.Simple(1, function() game.ConsoleCommand("quit" .. string.char(10)) end)
end
hook.Add("InitPostEntity", "jb_check", function() timer.Simple(5, run) end)
