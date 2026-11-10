-- Limita consumo de GPU; nao aumenta o FPS maximo do computador.
local desired = forge.config.fps or 60
assert(forge.set_fps_limit(desired), "Motor recusou o limite de FPS")
forge.log("Limite aplicado no motor: " .. forge.get_fps_limit())
