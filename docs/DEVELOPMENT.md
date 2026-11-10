# ForgeLoader — quero criar mods

O Dev Kit traz o gerador de projetos, exemplos Lua/C++, validador offline e fontes do runtime de fotos. O carregador geral e a API dentro do jogo ainda não estão implementados. Consulte [o estado das funções](STATUS.md) antes de distribuir exemplos como mods prontos.

## Começar sem decorar comandos

Extraia o ZIP **ForgeLoader-DevKit**. Instale Python 3.10+ no ambiente de desenvolvimento e abra **Abrir-DevKit.cmd**. O menu permite criar um projeto Lua e conferir os exemplos. O projeto novo fica em `MeusMods/autor.nome`.

O pacote para jogadores é outro download; ele não exige Python. O gerador não instala mods no jogo nem executa scripts Lua.

## Exemplos

- `modkit/examples/lua/kr_hello`: estrutura mínima de um script.
- `modkit/examples/lua/kr_observer`: observar evento e objeto Unreal usando APIs documentadas do UE4SS.
- `modkit/examples/native/kr_native`: ponto de entrada de módulo C++ para SDK UE4SS.
- `native/portraits`: integração nativa atual de fotos e RPC, específica do build analisado.

Os exemplos Lua/C++ ainda precisam de um adaptador UE4SS validado neste jogo. O EXE v3 atual não os carrega ao copiar para uma pasta. O C++ requer SDK/compilação compatíveis e não inclui DLL pronta.

## Pelo terminal

Da raiz do projeto:

```powershell
python modkit/krmodkit.py new autor.meumod --name 'Meu mod' --output MeusMods/autor.meumod
python modkit/krmodkit.py validate modkit/examples/lua
python -m unittest discover -s tests -v
```

Um mod de simulação deve usar `--required`. Mod local é apenas uma declaração de compatibilidade; não concede garantia de isolamento ou anticheat. Versões, arquivos e configurações dos módulos obrigatórios precisam coincidir nos perfis comparados. Fotos pessoais ficam fora do fingerprint.

## Compilar o runtime nativo

No Windows, com Git, Visual Studio C++ Build Tools e Windows SDK:

```powershell
powershell -NoProfile -File scripts/setup_native.ps1
powershell -NoProfile -File scripts/build_portraits.ps1
```

MinHook é baixado em commit fixo para `.local`. O compilador e SDK instalados são descobertos automaticamente. A DLL compilada pode ter outro hash; não substitua o artefato validado sem revisar o manifesto de compatibilidade e testar a nova compilação. O instalador publicado usa a DLL v3 já selecionada, não qualquer build local.

## Gerar downloads separados

```powershell
python scripts/build_releases.py --devkit-only
python scripts/build_releases.py --runtime-dll CAMINHO/KingdomsPortraits.dll
```

Os pacotes ficam em `dist/releases/v0.1.0-alpha`, acompanhados de `SHA256SUMS.txt` e `release-manifest.json`. A DLL precisa corresponder ao hash validado em `profiles/player-patch.json`.

O pacote de jogadores contém um patch pequeno de cabeçalhos PE e a DLL própria do projeto. O EXE original é fornecido pelo usuário e transformado localmente. Para gerar novamente o patch a partir das cópias originais exatas:

```powershell
python scripts/prepare_player_patch.py ORIGINAL.exe RETRATOS_V3.exe
```

## Ferramentas REA

O repositório mantém `tools/rea` e seus cinco submódulos fixados. Para obtê-los no Windows, use `scripts/initialize_rea.ps1`, que trata os fixtures com nomes incompatíveis com NTFS. Os testes do SDK/instalador não exigem clonar essas ferramentas.

Não há projeto Unreal original neste repositório. O uso do UE4SS está em avaliação, sem instalação automática. Mais detalhes do protótipo de SDK em [modkit/README.md](../modkit/README.md).
