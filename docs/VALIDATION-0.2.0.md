# Validação local da versão 0.2.0-alpha

Em 10/11/2026, no PC de desenvolvimento, o instalador do pacote para jogadores atualizou o runtime v3 com backup e os três arquivos `.flmod` foram instalados pelo instalador distribuído.

O jogo foi iniciado com o EXE suportado, em janela. Evidências observadas:

- Processo respondeu e o título mudou para `Kingdoms Reborn | ForgeLoader funcionando`.
- Relatório `mods-status.json` listou `forge.hello`, `forge.fps_limit` e `forge.native_hello` como `loaded`, sem erros.
- Log confirmou `Engine FPS limit requested=60.0 readback=60.0`.
- Callback Lua registrou execução durante dois segundos e o módulo DLL registrou seu tick.
- A criação do painel de mods foi registrada. A captura pelo helper Windows falhou com `FrameArrived timed out` e `window capture timed out`; aparência e cliques do painel não foram validados automaticamente.

Os testes nativos também executaram fontes Lua, uma DLL real, callback, orçamento de instruções, limite de memória, erro Lua em tick e na inicialização, dependência ausente/cíclica, caminho inválido, mod desativado e runtime incompatível. Erros Lua foram isolados por mod.

Os testes Python/PowerShell exercitam instalação `.flmod`, recusa de sobrescrita, travessia, colisões de caminho, nomes reservados e declarações incompatíveis, além da aplicação/restauração do patch em cópias temporárias.

Isto comprova carregamento e execução local dos exemplos, sem afirmar estabilidade de qualquer mod nativo, compatibilidade com outro build, comportamento entre dois PCs, aumento de FPS ou solução do crash original da GTX 1080.
