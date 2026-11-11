# ForgeLoader para Kingdoms Reborn 0.214

Este ramo mantém o port **0.2.1-KR214** para o build antigo. O pacote [0.2.0-alpha para 0.253](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/tag/v0.2.0-alpha) é separado.

- [Instalador para jogadores KR214](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.1-KR214/ForgeLoader-Players-0.2.1-KR214.zip)
- [Perfil leve GTX 1080 (.flmod)](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.1-KR214/forge.kr214_performance-1.0.0.flmod)
- [Dev Kit KR214](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.1-KR214/ForgeLoader-DevKit-0.2.1-KR214.zip)

Extraia o instalador, feche o jogo e abra `Instalar-ForgeLoader.cmd`. Selecione a pasta do **0.214**. Depois use **Instalar mod**, na janela do jogo, ou `ForgeLoader/Instalar-Mod.cmd`. Selecione o `.flmod`, reinicie e confira **Meus mods**.

O instalador inclui o reparador de saves e o perfil leve opcional. O mod `yongs.rejoin_fix` usa o arquivo original do autor; se já estiver na pasta `Mods`, não precisa reinstalá-lo. [Instalação, reparo e limites](docs/KR214.md) · [API](docs/MOD-API.md) · [Criar com IA](CRIAR-MOD-COM-IA.md).

## Validação

No PC de desenvolvimento, a instalação 0.214 abriu com `yongs.rejoin_fix` e o perfil leve carregados. O motor confirmou os limites gráficos, e o usuário confirmou que o seletor de `.flmod` abriu pelo botão. O reparador foi testado em cópias sintéticas e leu metadados antigos de referência sem alterá-los. Reconexão, recuperação de um save afetado e ganho de FPS no PC com GTX 1080 ainda precisam de teste.

O build usa o EXE exato e preserva as seções originais do jogo. Consulte `profiles/player-patch.json` para identidade do binário. A distribuição não inclui o jogo nem a DLL do mod de terceiros.

## Desenvolver

```powershell
python -m unittest discover -s tests -v
powershell -NoProfile -File scripts/setup_native.ps1
powershell -NoProfile -File scripts/build_portraits.ps1
python scripts/build_releases.py --devkit-only
```

O build compila o runtime e os mods nativos. [Guia do Dev Kit](docs/DEVELOPMENT.md). REA e os submódulos continuam fixados em `tools/rea`. Não inclua binários do jogo, saves, fotos ou logs privados no Git.
