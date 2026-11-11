# API ForgeLoader 0.2 (major 1)

O runtime carrega `Mods/autor.nome/mod.json` na raiz do jogo. O arquivo `.flmod` é um ZIP com `mod.json` na raiz, pronto para o instalador. O runtime lê as pastas na inicialização; reinicie após instalar, remover ou editar um mod.

## Lua 5.4.9 integrado

Use `runtime: forgeloader-lua` e `entrypoint: Scripts/main.lua`. O gerador do Dev Kit já usa esse contrato. Não depende de uma instalação do Lua ou do UE4SS.

| Função | Efeito |
| --- | --- |
| `forge.log(texto)` | Registra mensagem no log do ForgeLoader |
| `forge.set_window_title(texto)` | Altera o título da janela; retorna sucesso |
| `forge.set_fps_limit(numero)` | Chama `UEngine::SetMaxFPS`; aceita 0 (sem limite) ou 15–240; retorna sucesso após leitura de confirmação |
| `forge.get_fps_limit()` | Lê o limite do motor, não o FPS medido |
| `forge.on("tick", funcao)` | Um callback por mod, com segundos desde o frame anterior, limitados a 1 |
| `forge.on("lobby_tick", funcao)` | Um callback por mod quando a UI de lobby atualiza; argumento 0 nesta versão |
| `forge.config` | Tabela das configurações `settings` do manifesto |
| `forge.version` | Versão do loader |

Bibliotecas disponíveis: base, table, string, math e utf8. `io`, `os`, `package`, `debug`, `load`, `loadfile`, `dofile` e `print` não são disponibilizados. Cada mod recebe estado separado, limite de 8 MiB e orçamento por chamada de 200 mil instruções/50 ms verificado pelo hook a cada mil instruções. Funções C das bibliotecas não são interrompidas durante sua execução: esses limites são proteção contra erros comuns, sem promessa de executar código hostil com segurança. Erros desativam o mod e aparecem em **Meus mods** e no relatório.

## C++ nativo

Use `runtime: forgeloader-native`, `entrypoint: dlls/main.dll` e compile x64 com o cabeçalho `native/loader/forgeloader_api.h`. Exporte `ForgeMod_Load`; veja `modkit/examples/native/forge_native/main.cpp`. ABI, ID e versão exportados devem corresponder ao manifesto. O host fornece as mesmas funções locais. Callbacks e entrada executam na thread do jogo.

Uma DLL nativa tem os privilégios do processo e pode travar o jogo. Não há descarregamento ou atualização a quente. APIs diretas do Unreal além do cabeçalho exigem integração própria e validação para o hash do build; esta versão não oferece acesso Lua genérico a todos os objetos/Blueprints.

## Compatibilidade e diagnóstico

O loader verifica API major, hash do build, IDs, versões exatas de dependências, ciclos, conflitos e arquivo de entrada. `core.shared_portraits: 3.0.0` identifica o protocolo de retratos existente. `ue4ss-lua`/`ue4ss-native` continuam reconhecidos pelo validador offline para projetos antigos, mas são recusados pelo runtime integrado: precisam ser portados.

Esta versão executa somente `multiplayer: local`. Mods de simulação devem continuar declarando `required` e serão recusados até existir negociação no lobby. Não marque um mod de gameplay como local para contornar isso. O recurso de fotos existente continua incluído, mas recepção entre dois PCs ainda precisa de teste.

Relatório: `%LOCALAPPDATA%\PunCity\Saved\ForgeLoader\mods-status.json`. Log: `runtime.log` na mesma pasta. O limite de FPS é de sessão, sem alteração permanente nos INIs, e não representa uma otimização medida.

Dependências fixadas em `profiles/loader-dependencies.json`: [Lua 5.4](https://www.lua.org/manual/5.4/manual.html), [nlohmann/json 3.12.0](https://github.com/nlohmann/json/releases/tag/v3.12.0). Licenças em `third_party`.

## Exports adicionais no KR214

`ForgeLoader_GameBase()` fornece a base validada da imagem. `ForgeLoader_Hook(rva, detour, original)` funciona na inicialização nativa, apenas em seções executáveis do jogo. Retorna 0 no sucesso; hooks são removidos se a inicialização não for confirmada. `ForgeLoader_ClampVideo214` usa a interface em `native/loader/kr214_video_api.h` para limites gráficos predefinidos. Esses exports não são parte da ABI genérica de outros builds.
