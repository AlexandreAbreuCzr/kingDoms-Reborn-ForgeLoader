# ForgeLoader para Kingdoms Reborn

Instale mods Lua e C++ no Kingdoms Reborn. A versão **0.2.0-alpha** inclui o carregador, o importador de fotos e exemplos que executam dentro do jogo.

## Downloads

| Quero | Arquivo |
| --- | --- |
| Instalar o ForgeLoader no jogo | [ForgeLoader para jogadores](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.0-alpha/ForgeLoader-Players-0.2.0-alpha.zip) |
| Criar mods, inclusive com IA | [Dev Kit](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.0-alpha/ForgeLoader-DevKit-0.2.0-alpha.zip) |
| Testar meu primeiro mod | [Título da janela](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.0-alpha/forge.hello-1.0.0.flmod) |
| Limitar o consumo de GPU | [Limite de 60 FPS](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.0-alpha/forge.fps_limit-1.0.0.flmod) |
| Estudar um mod nativo compilado | [Exemplo C++](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases/download/v0.2.0-alpha/forge.native_hello-1.0.0.flmod) |

## Instalar e usar

1. Extraia o pacote para jogadores, feche o jogo e abra **Instalar-ForgeLoader.cmd**. Escolha a pasta do jogo.
2. Baixe um mod `.flmod`. Abra **Instalar mod** dentro do jogo ou **ForgeLoader/Instalar-Mod.cmd** na pasta do jogo e selecione o arquivo.
3. Reinicie o jogo e use **Meus mods** para conferir o resultado. O mod de exemplo muda o título da janela.

Você também pode copiar a pasta descompactada para `Mods/autor.nome/`, com `mod.json` diretamente dentro dela. `.flmod` é um ZIP, não um JAR. Não copie apenas o arquivo `.flmod` para Mods: use o instalador ou extraia sua pasta.

O download não inclui o jogo e não exige Python, Lua ou compilador para jogar. Há backup e restauração. O pacote para jogadores já traz dois mods de exemplo para instalar opcionalmente.

## Recursos e limites

- Runtime Lua 5.4.9 integrado, módulos DLL x64 com ABI C e callbacks na thread do jogo.
- Verificação de build/API, dependências, versões, ciclos e conflitos; relatório de erros por mod.
- API inicial para logs, título, limite de FPS e eventos. [API e formato dos pacotes](docs/MOD-API.md).
- Importador PNG/JPG em **Configurações do Líder**, preservando o protótipo de fotos compartilhadas.

Os três exemplos foram executados no jogo local. O carregador ainda aceita **mods locais**; a negociação no lobby e mods de simulação compartilhada estão em desenvolvimento. A recepção das fotos em outro PC ainda não foi validada. Não há ganho de FPS medido nem correção confirmada para o crash da GTX 1080. O limite de FPS reduz a taxa máxima; não aumenta o desempenho do computador.

Este adaptador aceita o build 0.253 identificado pelo hash em `profiles/player-patch.json`. Outros builds precisam de adaptação. Mods de UE4SS e de outros jogos não são carregados automaticamente.

[Guia para jogadores](docs/PLAYERS.md) · [Criar mods](docs/DEVELOPMENT.md) · [Criar com IA](CRIAR-MOD-COM-IA.md) · [Estado](docs/STATUS.md) · [Validação desta versão](docs/VALIDATION-0.2.0.md) · [Todas as versões](https://github.com/AlexandreAbreuCzr/kingDoms-Reborn-ForgeLoader/releases)

## Código e desenvolvimento

`native/loader` contém o loader e a ABI; `native/portraits` contém o adaptador do jogo e as fotos; `modkit` contém gerador, empacotador e exemplos; `installer` contém os instaladores. `tools/rea` mantém REA e seus submódulos fixados. Binários, fotos, saves, backups e diagnósticos pessoais ficam fora do Git.

```powershell
python -m unittest discover -s tests -v
powershell -NoProfile -File scripts/setup_native.ps1
powershell -NoProfile -File scripts/build_portraits.ps1
```

O CI compila Lua, loader, exemplo C++ e executa os testes nativos. Testes que precisam do jogo original são pulados quando o fixture não é fornecido. Não há execução do jogo no CI. [Contribuir](CONTRIBUTING.md).
