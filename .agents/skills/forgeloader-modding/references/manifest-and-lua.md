# Manifesto e Lua

Os caminhos abaixo são relativos à raiz do Dev Kit identificada para a tarefa. A implementação de referência é `modkit/krmodkit.py`; use seus valores atuais de API/build em vez de copiar hashes de uma conversa antiga.

## Criar a estrutura

```powershell
python modkit/krmodkit.py new autor.nome --name 'Nome do mod' --output MeusMods/autor.nome
python modkit/krmodkit.py validate MeusMods
python modkit/krmodkit.py pack MeusMods/autor.nome --output Pacotes/autor.nome.flmod
```

Acrescente `--required` para alterações de regras ou simulação. O runtime 0.2 recusa esses mods enquanto não houver handshake. O gerador recusa um destino existente; para editar um mod, leia seus arquivos e preserve as alterações do autor. Instale o `.flmod` pelo seletor do ForgeLoader e reinicie; ou copie a pasta para `Mods/autor.nome` na raiz do jogo.

## Contrato atual

| Campo | Regra |
| --- | --- |
| `schema` | Inteiro 1 |
| `id` | Letras minúsculas, dígitos e `_`, com namespace como `autor.nome`; `core.` é reservado |
| `version` | `X.Y.Z` |
| `api_major` | Major aceito pelo código atual do kit |
| `runtime` | `forgeloader-lua` ou `forgeloader-native` no runtime integrado; UE4SS legado apenas no validador offline |
| `entrypoint` | Arquivo existente dentro da pasta do mod, caminho relativo com `/` |
| `game_builds` | Lista explícita de hashes SHA-256 suportados |
| `multiplayer` | `local` ou `required` |
| `requires` | IDs e versões exatas das dependências |
| `conflicts` | Lista de IDs incompatíveis |
| `enabled` | Booleano opcional |

O validador também detecta ciclos e IDs duplicados. Um módulo obrigatório não pode depender de um módulo declarado apenas local. `package_hash` considera os arquivos do pacote e normaliza JSON; fotos e dados pessoais não devem ser colocados dentro do pacote de código.

## Scripts e APIs

`modkit/examples/forgeloader/forge.hello` e `forge.fps_limit` usam a API integrada. Leia `docs/MOD-API.md` e a implementação `native/loader/loader.cpp` antes de escolher funções. `forge.log`, `set_window_title`, `set_fps_limit`, `get_fps_limit`, `on`, `config` e `version` são os pontos de entrada desta versão.

Cada mod Lua usa estado separado e callbacks na thread do jogo. Use `forge.log` para mensagens; `print`, `io`, `os`, `package`, `debug` e carregamento dinâmico de fontes não são disponibilizados. Não prometa uma sandbox para código hostil: chamadas C não são preemptadas pelo orçamento de instruções.

Os projetos antigos em `modkit/examples/lua` usam APIs UE4SS (`RegisterHook`, `FindFirstOf`); elas não existem no runtime ForgeLoader. Porte o projeto ou implemente o adaptador necessário; não copie essas chamadas para um mod apresentado como executável.

## Perfis offline

```powershell
python modkit/krmodkit.py profile --game-exe CAMINHO/PrototypeCity-Win64-Shipping.exe --mods MeusMods --output artifacts/perfil.json
python modkit/krmodkit.py compare artifacts/host.json artifacts/convidado.json
```

O gerador confere o EXE e o runtime conhecidos. Não altere esses hashes só para aceitar um build diferente: outro build precisa de adaptação e testes. O comparador não instala módulos, não executa Lua e não bloqueia jogadores no lobby.
