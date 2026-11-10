# Criar mods ForgeLoader

O Dev Kit 0.2 inclui o gerador, o empacotador `.flmod`, exemplos Lua/C++ e fontes do loader e adaptador. O pacote para jogadores é separado e não requer Python.

## Primeiro mod

Extraia o Dev Kit, instale Python 3.10+ e abra **Abrir-DevKit.cmd**. Ou use:

```powershell
python modkit/krmodkit.py new autor.meumod --name 'Meu mod' --output MeusMods/autor.meumod
python modkit/krmodkit.py validate MeusMods
python modkit/krmodkit.py pack MeusMods/autor.meumod --output Pacotes/autor.meumod.flmod
```

Edite `Scripts/main.lua` e use a [API implementada](MOD-API.md). Instale o pacote com **Instalar mod** no jogo e reinicie. O CLI valida e empacota; a execução ocorre no runtime do jogo.

## Exemplos

- `modkit/examples/forgeloader/forge.hello`: título da janela e callback tick.
- `modkit/examples/forgeloader/forge.fps_limit`: limite de FPS do motor.
- `modkit/examples/native/forge_native`: DLL x64 com entrada `ForgeMod_Load`; compilada pelo script de build.
- `modkit/examples/lua` e `native/kr_native`: referências antigas de UE4SS; não executam no runtime integrado sem portabilidade.

O runtime oferece API local inicial. Lua genérico para qualquer UObject, novos assets e simulação compartilhada exigem novas integrações. Um mod de simulação deve declarar `--required` e será recusado pelo runtime 0.2 até existir handshake. Não altere essa declaração para contornar a verificação.

## Criar com IA

O menu **4 — Criar mod com IA** mostra o [guia](../CRIAR-MOD-COM-IA.md). O Dev Kit inclui `AGENTS.md` e a skill `forgeloader-modding`. Abra a pasta no seu assistente e peça a leitura das instruções e da API. Não há modelo ou chave de IA embutidos.

## Compilar

Windows, Git, Visual Studio C++ Build Tools e Windows SDK:

```powershell
powershell -NoProfile -File scripts/setup_native.ps1
powershell -NoProfile -File scripts/build_portraits.ps1
python -m unittest discover -s tests -v
```

MinHook é fixado por commit. Lua 5.4.9 e nlohmann/json 3.12.0 são baixados e verificados por SHA-256 em `.local`. O build executa testes de protocolo, imagens, Lua, DLL, callbacks, erros, limites e dependências. A DLL sai em `.local/portrait-build/KingdomsPortraits.dll`, com o exemplo nativo na mesma pasta.

Uma compilação diferente requer revisar o hash do runtime no perfil e no kit após validação. Nunca remova o guard do EXE para aceitar outro build: os RVAs são específicos.

## Pacotes e REA

```powershell
python scripts/build_releases.py --devkit-only
python scripts/build_releases.py --runtime-dll .local/portrait-build/KingdomsPortraits.dll
```

Downloads separados, exemplos `.flmod`, hashes e manifesto ficam em `dist/releases/v0.2.0-alpha`. O pacote para jogadores distribui a DLL própria e um patch de cabeçalhos PE aplicado à cópia original do usuário; não inclui o jogo.

`tools/rea` mantém REA e seus cinco submódulos fixados. `scripts/initialize_rea.ps1` trata fixtures incompatíveis com NTFS. Não há projeto Unreal original neste repositório. [Estado](STATUS.md) e [API](MOD-API.md).
