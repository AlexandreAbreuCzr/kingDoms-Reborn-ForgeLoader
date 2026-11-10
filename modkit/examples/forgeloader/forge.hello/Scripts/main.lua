forge.log("Exemplo Lua carregado")
assert(forge.set_window_title(forge.config.title), "Nao foi possivel alterar o titulo")
local elapsed = 0
local reported = false
forge.on("tick", function(dt)
    elapsed = elapsed + dt
    if elapsed >= 2 and not reported then
        reported = true
        forge.log("Callback tick executou no jogo por 2 segundos")
    end
end)
