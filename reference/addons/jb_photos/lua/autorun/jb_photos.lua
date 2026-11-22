-- PHOTOS AUTOMATIQUES de rp_cw_battle_of_jabiim (LOCAL UNIQUEMENT : copié puis retiré par Claude, jamais publié).
-- Téléporte le joueur sur chaque point de vue, cache le HUD et capture l'écran en JPG dans data/jb_photos/.
local DIR = "jb_photos"
local VIEWS = {
    {n="w_generatorconsole", p=Vector(6064,2775,88), a=Angle(25,105,0)},
    {n="w_bunker_caisses", p=Vector(-9150,-4040,10), a=Angle(40,225,0)},
}
if SERVER then
    util.AddNetworkString("jb_photo")
    hook.Add("PlayerInitialSpawn", "jb_photos_start", function(ply)
        if game.GetMap() ~= "rp_cw_battle_of_jabiim" then return end
        file.CreateDir(DIR)
        local t = 14
        for _, v in ipairs(VIEWS) do
            timer.Simple(t, function()
                if not IsValid(ply) then return end
                ply:SetMoveType(MOVETYPE_NOCLIP)
                local p = v.p
                if v.sol then          -- altitude inconnue : on pose la caméra 60 au-dessus du sol trouvé
                    local tr = util.TraceLine({start = p, endpos = p - Vector(0, 0, 6000), mask = MASK_SOLID_BRUSHONLY})
                    p = tr.HitPos + Vector(0, 0, 60)
                end
                ply:SetPos(p - Vector(0, 0, 64))
                ply:SetEyeAngles(v.a)
            end)
            timer.Simple(t + 4, function()
                if IsValid(ply) then net.Start("jb_photo") net.WriteString(v.n) net.Send(ply) end
            end)
            t = t + 6
        end
        timer.Simple(t + 2, function() file.Write(DIR .. "/done.txt", "ok") end)
    end)
else
    local pending
    net.Receive("jb_photo", function() pending = net.ReadString() end)
    hook.Add("HUDShouldDraw", "jb_photos_nohud", function(n) if n ~= "CHudGMod" then return false end end)
    hook.Add("PostRender", "jb_photos_capture", function()
        if not pending then return end
        local name = pending
        pending = nil
        local data = render.Capture({ format = "jpeg", quality = 90, x = 0, y = 0, w = ScrW(), h = ScrH() })
        file.CreateDir(DIR)
        if data then file.Write(DIR .. "/" .. name .. ".jpg", data) end
    end)
end
