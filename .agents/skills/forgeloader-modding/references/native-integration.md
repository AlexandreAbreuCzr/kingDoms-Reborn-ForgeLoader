# Integração nativa e runtime

Use estes critérios quando a tarefa exigir C++, hooks ou alteração do adaptador. Eles não são uma lista de APIs garantidas para todo mod.

## Pontos de partida

- `modkit/examples/native/kr_native`: exemplo-fonte de ciclo de vida C++ do UE4SS. Ele depende do SDK escolhido; não inclui DLL já testada no jogo.
- `native/portraits/portraits.cpp`: integração atual do importador e das rotinas nativas de retrato.
- `scripts/native_symbols.py` e `scripts/pdb_types.py`: identidade PE/PDB, símbolos e layouts do build fornecido.
- `scripts/setup_native.ps1` e `scripts/build_portraits.ps1`: dependência MinHook fixada, compilação e testes nativos.
- `profiles/player-patch.json` e `scripts/prepare_player_patch.py`: aplicação local do bootstrap ao EXE exato.

## Evidência antes da chamada

Para um ponto de entrada novo, valide o build, a assinatura/ABI x64 e o layout dos objetos envolvidos. Um RVA do build antigo não é um endereço universal. Use ASLR corretamente e preserve as verificações de identidade do adaptador.

A pasta de fontes do projeto não é o projeto Unreal original. Um símbolo no PDB pode ser uma função não refletida; a API Lua pode não conseguir chamá-la. Novos modelos, mapas e Blueprints também podem exigir pipeline de assets/cooking compatível.

Mantenha a procedência: consultas DbgHelp, desmontagem e decompilação são evidências distintas. As ferramentas REA e os submódulos existem em `tools/rea`, mas a presença delas não comprova que uma decompilação foi concluída.

## Invariantes relevantes do runtime de fotos

- Chamadas sobre widgets, prévia do líder e RPCs são feitas no contexto da thread do jogo. O seletor de arquivo só coloca uma ação na fila.
- A prévia nativa enviada pelo botão Finalizado precisa permanecer coerente com o retrato selecionado; alterar somente uma cópia do GameInstance pode ser desfeito pela própria tela.
- Memória de `FString` do Unreal usa o alocador correspondente. Uma struct emprestada não deve receber destruição nativa como se fosse uma cópia pertencente ao módulo.
- Referências fracas do Unreal e os limites de imagem/cache evitam manter ponteiros crus para objetos coletados. Preserve limites na recepção, não apenas no seletor local.
- O código atual de fotos usa um canal específico de informações de jogador. Ele não é uma API genérica de distribuição de código ou um handshake de mods.

O patch gráfico NoAsync não faz parte do runtime de fotos atual. Não introduza uma mitigação gráfica experimental em um mod cosmético sem justificativa e escopo correspondentes.

## Compilar e testar

Compile usando as dependências fixadas do projeto quando a tarefa permitir. Um novo hash de DLL precisa de revisão de compatibilidade e validação; não remova a checagem de identidade para forçar instalação.

Exercite patch, backup e restauração em arquivos temporários. Relate testes que exigem o jogo e não puderam ser executados. Para afirmar funcionamento em rede, é necessário observar o caminho receptor em outro cliente; uma chamada local do RPC não basta.
