# ForgeLoader — orientação para assistentes de código

Este repositório e o Dev Kit permitem criar projetos de mods e desenvolver o runtime de Kingdoms Reborn. Para criar ou revisar um mod, use a skill em `.agents/skills/forgeloader-modding/SKILL.md`.

Antes de escolher uma integração, confira `release.json`, `modkit/STATUS.json` e `docs/STATUS.md`. Esses arquivos distinguem ferramentas disponíveis de funcionalidades ainda não implementadas. Não deduza a existência de uma API pelo nome ForgeLoader.

- Projetos de exemplo do usuário ficam normalmente em `MeusMods/autor.nome`; preserve destinos que ele indicar.
- `modkit/krmodkit.py` define o manifesto aceito, dependências e comparação offline. Prefira o gerador existente para criar a estrutura.
- `native/loader/` contém Lua e a ABI C; `native/portraits/` integra ao build do jogo. Use `docs/MOD-API.md` e os exemplos executáveis em `modkit/examples/forgeloader` e `native/forge_native`. Os exemplos UE4SS antigos exigem portabilidade.
- Mods que alteram simulação devem declarar `multiplayer: required`. Fotos pessoais não entram no fingerprint de código. O comparador offline não é negociação no lobby nem anticheat.
- Use testes proporcionais à alteração. Para testar patch/instalação, use cópias temporárias; os testes que precisam do jogo original aceitam `KINGDOMS_ORIGINAL_EXE` e podem ser pulados quando o fixture não existe.
- Relate separadamente estrutura criada, validação offline, compilação, execução local no jogo e teste entre clientes. Não transforme um teste de uma dessas camadas em confirmação das outras.

Guias para o usuário: `CRIAR-MOD-COM-IA.md` e `docs/DEVELOPMENT.md`.
