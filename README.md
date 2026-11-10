# ForgeLoader para Kingdoms Reborn

Uma base comunitária para retratos personalizados e, futuramente, mods em Lua/C++. O projeto está em **alpha**. O runtime atual oferece os retratos; o carregador geral de mods ainda está em desenvolvimento.

## Escolha seu download

| Quero… | Download | Como usar |
| --- | --- | --- |
| **Jogar com os retratos** | [ForgeLoader para jogadores](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.1.0-alpha/ForgeLoader-Players-0.1.0-alpha.zip) | Extraia, abra `Instalar-ForgeLoader.cmd` e escolha a pasta do jogo. |
| **Criar e estudar mods** | [ForgeLoader Dev Kit](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.1.0-alpha/ForgeLoader-DevKit-0.1.0-alpha.zip) | Extraia e abra `Abrir-DevKit.cmd`. Requer Python 3.10+ para desenvolvimento. |

[Todos os arquivos e versões](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases) · [Guia para jogadores](docs/PLAYERS.md) · [Guia do Dev Kit](docs/DEVELOPMENT.md)

O download para jogadores aplica o runtime à sua cópia existente do jogo, com backup. Não inclui o jogo completo e não exige Dev Kit, Python ou compilador. Os arquivos de conferência SHA-256 ficam junto aos downloads na Release.

## O que já funciona

- Importador de PNG/JPG em **Configurações do Líder**.
- Foto normalizada para 128 × 128 e até 8 KiB, com remoção/restauração do retrato.
- Instalador com conferência do build, backup e restauração.
- Gerador de projetos, exemplos Lua/C++ e verificação offline de dependências/arquivos.

O código de fotos foi preparado para transmitir a imagem pela partida. Cada jogador não precisa copiar a foto manualmente; todos precisam do runtime compatível. A recepção em outro PC ainda aguarda teste real.

## O que ainda está em desenvolvimento

Copiar novos mods para uma pasta ainda não os carrega. Faltam o carregador geral, a API integrada e a checagem de compatibilidade no lobby. Os exemplos Lua/C++ são materiais de desenvolvimento, não mods de gameplay já validados. Não há ganho de FPS medido ou correção confirmada para a GTX 1080.

Veja [o estado de cada função](docs/STATUS.md), [próximas etapas](docs/ROADMAP.md) e [histórico de versões](CHANGELOG.md).

## Organização do código

```text
installer/          Instalação e restauração para jogadores
native/portraits/   Runtime nativo de retratos v3
modkit/             Ferramentas do SDK e exemplos Lua/C++
profiles/           Identificação do build e patch de cabeçalhos PE
scripts/            Compilação, empacotamento e análise
tests/              Testes automatizados
docs/               Guias de uso, desenvolvimento e roadmap
tools/rea/          REA e seus submódulos fixados
```

Downloads compilados ficam em Releases. `dist/`, backups, diagnósticos, saves, fotos e binários do jogo ficam fora do Git.

## Desenvolver

```powershell
git clone https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader.git
cd kingDoms-Reborn-ForgeLoader
python -m unittest discover -s tests -v
python scripts/build_releases.py --devkit-only
```

Os testes que exigem o EXE original são pulados se ele não for fornecido. Para validar o patch real, defina `KINGDOMS_ORIGINAL_EXE` com uma cópia original do build suportado. O CI também compila os fontes nativos e executa seus testes, sem executar o jogo.

Para obter as ferramentas REA no Windows: `powershell -NoProfile -File scripts/initialize_rea.ps1`. Para o runtime, consulte [compilação no guia de desenvolvimento](docs/DEVELOPMENT.md).

[Como contribuir](CONTRIBUTING.md) · [Relatar um problema](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/issues/new/choose)
