-- MESURE DE FPS de rp_cw_battle_of_jabiim (outil local, jamais publié) : sur chaque point de vue, 2 s de stabilisation
-- puis 5 s de mesure des images ; écrit data/jb_fps/result.txt (moyenne, 1 % le plus lent).
if game.GetMap() ~= "rp_cw_battle_of_jabiim" then return end
local VIEWS = {
    {n="village_place", p=Vector(-1300,8300,180), a=Angle(4,100,0)},
    {n="village_aerien", p=Vector(-1400,4600,1917), a=Angle(24,95,0)},
    {n="interieur_atelier", p=Vector(683,10497,190), a=Angle(12,16,0)},
    {n="fermes_plaines", p=Vector(6500,7300,1069), a=Angle(6,200,0)},
    {n="mine_bord", p=Vector(3400,-2400,1621), a=Angle(22,140,0)},
    {n="mine_fond", p=Vector(-1024,-200,-1100), a=Angle(-2,95,0)},
    {n="raffinerie", p=Vector(4000,1000,340), a=Angle(6,35,0)},
    {n="front_aerien", p=Vector(0,-9200,1353), a=Angle(20,92,0)},
    {n="no_mans_land", p=Vector(-3200,-7200,140), a=Angle(2,85,0)},
    {n="fob", p=Vector(0,-8700,425), a=Angle(12,270,0)},
}
if SERVER then
    util.AddNetworkString("jb_fps_go")
    hook.Add("PlayerInitialSpawn", "jb_fps", function(ply)
        local t = 20
        for i, v in ipairs(VIEWS) do
            timer.Simple(t, function()
                if not IsValid(ply) then return end
                ply:SetMoveType(MOVETYPE_NOCLIP); ply:SetPos(v.p); ply:SetEyeAngles(v.a)
                net.Start("jb_fps_go"); net.WriteUInt(i, 8); net.Send(ply)
            end)
            t = t + 8
        end
    end)
else
    local res, cur, samples = {}, nil, {}
    net.Receive("jb_fps_go", function()
        local i = net.ReadUInt(8)
        timer.Simple(2, function() cur, samples = i, {} end)
        timer.Simple(7, function()
            cur = nil
            table.sort(samples)
            local n, sum = #samples, 0
            for _, f in ipairs(samples) do sum = sum + f end
            local low = samples[math.max(1, math.floor(n * 0.01))] or 0
            res[#res + 1] = string.format("%-18s moyenne %5.0f ips   1%% bas %5.0f ips   (%d images)", VIEWS[i].n, n > 0 and sum / n or 0, low, n)
            if i == #VIEWS then
                file.CreateDir("jb_fps")
                file.Write("jb_fps/result.txt", table.concat(res, "\n") .. "\n")
            end
        end)
    end)
    hook.Add("Think", "jb_fps", function() if cur then samples[#samples + 1] = 1 / math.max(RealFrameTime(), 1e-4) end end)
    hook.Add("HUDShouldDraw", "jb_fps", function(n) if cur then return false end end)
end
