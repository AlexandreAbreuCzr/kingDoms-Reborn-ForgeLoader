-- Read-only UE4SS example. It does not change gameplay or send game data.
-- RegisterHook requires the UFunction to exist when this script initializes.
local ok, pre_id, post_id = pcall(function()
    return RegisterHook("/Script/Engine.PlayerController:ClientRestart", function()
        local instance = FindFirstOf("PunGameInstance")
        if instance and instance:IsValid() then
            print("[examples.observer] Controller reiniciado; PunGameInstance encontrado\n")
        else
            print("[examples.observer] PunGameInstance ainda indisponivel\n")
        end
    end)
end)
if not ok then
    print("[examples.observer] Hook indisponivel; verificar adaptador e ordem de inicializacao\n")
end
-- A runtime integration must retain pre_id/post_id and unregister on unload.
