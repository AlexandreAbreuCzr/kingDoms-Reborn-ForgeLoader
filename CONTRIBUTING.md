# Contribuir com o ForgeLoader

Comece pelo [guia do Dev Kit](docs/DEVELOPMENT.md) e pelo [estado atual](docs/STATUS.md).

- Use uma branch `codex/descricao` ou uma branch descritiva da sua contribuição.
- Mantenha alterações de interface, rede e desempenho em módulos separados.
- Documente o build do jogo e a versão da API que testou.
- Rode `python -m unittest discover -s tests -v`; não declare testes de jogo que não executou.
- Não adicione EXEs do jogo, DLLs compiladas, PDBs, PAKs, saves, dumps, fotos pessoais ou credenciais ao Git.
- Os downloads compilados ficam em Releases e passam pelo empacotador com allowlist.

Um mod que altera a simulação precisa declarar compatibilidade obrigatória e passar por teste multiplayer. Um fingerprint igual não prova comportamento determinístico.
