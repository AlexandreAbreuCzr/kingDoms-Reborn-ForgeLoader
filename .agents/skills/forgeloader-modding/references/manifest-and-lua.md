# Manifesto e Lua

Os caminhos abaixo são relativos à raiz do Dev Kit identificada para a tarefa. A implementação de referência é `modkit/krmodkit.py`; use seus valores atuais de API/build em vez de copiar hashes de uma conversa antiga.

## Criar a estrutura

```powershell
python modkit/krmodkit.py new autor.nome --name 'Nome do mod' --output MeusMods/autor.nome
python modkit/krmodkit.py validate MeusMods
```

Acrescente `--required` para alterações de regras ou simulação. O gerador recusa um destino existente; para editar um mod, leia seus arquivos e preserve as alterações do autor.

## Contrato atual

| Campo | Regra |
| --- | --- |
| `schema` | Inteiro 1 |
| `id` | Letras minúsculas, dígitos e `_`, com namespace como `autor.nome`; `core.` é reservado |
| `version` | `X.Y.Z` |
| `api_major` | Major aceito pelo código atual do kit |
| `runtime` | `ue4ss-lua` ou `ue4ss-native` |
| `entrypoint` | Arquivo existente dentro da pasta do mod, caminho relativo com `/` |
| `game_builds` | Lista explícita de hashes SHA-256 suportados |
| `multiplayer` | `local` ou `required` |
| `requires` | IDs e versões exatas das dependências |
| `conflicts` | Lista de IDs incompatíveis |
| `enabled` | Booleano opcional |

O validador também detecta ciclos e IDs duplicados. Um módulo obrigatório não pode depender de um módulo declarado apenas local. `package_hash` considera os arquivos do pacote e normaliza JSON; fotos e dados pessoais não devem ser colocados dentro do pacote de código.

## Scripts e APIs

`modkit/examples/lua/kr_hello/Scripts/main.lua` demonstra a entrada de um script. `kr_observer` usa `RegisterHook` e `FindFirstOf` documentados pelo UE4SS. Isso não confirma sua execução neste build do jogo.

Antes de usar uma função nova, encontre sua definição no adaptador ou na documentação primária da dependência fixada. Para `RegisterHook`, a `UFunction` precisa existir em memória no momento do registro. Um evento não refletido pode exigir outro ponto de entrada nativo. Não invente um namespace `ForgeLoader.*` quando ele não existir no código.

Fontes: [RegisterHook](https://docs.ue4ss.com/lua-api/global-functions/registerhook.html), [FindFirstOf](https://docs.ue4ss.com/lua-api/global-functions/findfirstof.html).

## Perfis offline

```powershell
python modkit/krmodkit.py profile --game-exe CAMINHO/PrototypeCity-Win64-Shipping.exe --mods MeusMods --output artifacts/perfil.json
python modkit/krmodkit.py compare artifacts/host.json artifacts/convidado.json
```

O gerador confere o EXE e o runtime conhecidos. Não altere esses hashes só para aceitar um build diferente: outro build precisa de adaptação e testes. O comparador não instala módulos, não executa Lua e não bloqueia jogadores no lobby.
