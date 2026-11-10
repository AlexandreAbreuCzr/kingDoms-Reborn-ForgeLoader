---
name: forgeloader-modding
description: Criar, editar e revisar mods de Kingdoms Reborn usando o ForgeLoader Dev Kit, incluindo manifestos, exemplos Lua/C++, compatibilidade multiplayer e integrações nativas. Use em pedidos de desenvolvimento de mods deste projeto, não em dicas de gameplay ou instalação de outros jogos.
---

# ForgeLoader Modding

Trabalhe no pedido concreto do usuário usando as capacidades que o projeto realmente oferece. Esta skill pode ser distribuída com o Dev Kit ou copiada inteira para outro ambiente; seus arquivos de referência ficam dentro desta pasta.

## Localizar o projeto e as capacidades

Localize a pasta indicada pelo usuário que contém `release.json` e `modkit/krmodkit.py`. Se a skill estiver instalada fora do projeto, não trate sua própria pasta como raiz do Dev Kit. Leia as instruções locais aplicáveis e confira `release.json`, `modkit/STATUS.json` e `docs/STATUS.md`.

Esses estados mudam com as versões. A existência de exemplos, de um manifesto válido ou de uma função nos headers não demonstra que o carregador, a API ou o canal de rede correspondente estão implementados. Identifique no código o ponto de entrada que fará o recurso executar.

## Escolher a implementação

- Para um projeto Lua ou suas dependências, use [manifesto e scripts](references/manifest-and-lua.md). Consulte `modkit/examples/forgeloader` e prefira gerar e empacotar pelo CLI existente. A API executada está em `docs/MOD-API.md`.
- Para módulo C++, hook ou acesso a propriedades nativas, use [integração nativa](references/native-integration.md). Consulte `modkit/examples/native` e o runtime já existente em `native/portraits` conforme a tarefa.
- Se o pedido depende de uma API ausente, identifique a integração necessária. Implemente a ponte quando fizer parte do escopo solicitado; caso contrário, entregue a estrutura útil com essa dependência marcada como pendente. Não substitua chamadas inexistentes por código apresentado como funcional.

Use o destino solicitado pelo usuário; na ausência de outro, `MeusMods/autor.nome` mantém o projeto separado dos exemplos de referência. Um mod de gameplay pode precisar de Lua e de um adaptador nativo; escolha pela API disponível, não pela extensão preferida.

## Compatibilidade e fotos

Marque como `required` o mod que altera simulação, recursos, regras ou resultados compartilhados. `local` é apropriado quando o comportamento se limita ao cliente. Uma declaração local não isola o código nem garante determinismo.

Verifique dependências e conflitos pelo validador. Versão, build e fingerprints são evidências de configuração; não comprovam negociação de rede nem recepção no outro PC. Ao trabalhar com retratos, preserve a distinção entre módulo compartilhado e foto pessoal: cada jogador pode usar uma imagem diferente, transmitida pelo canal de dados, sem incluir as fotos no fingerprint dos mods.

## Verificar e entregar

Execute a validação do manifesto após criar ou alterar um pacote. Use testes que exercitem o comportamento alterado; uma mudança apenas textual não exige inventar testes. Compile o C++ quando houver ambiente e dependências disponíveis. Teste escrita de patch ou instalação em cópias temporárias.

No resultado, informe o que foi implementado, os arquivos de entrada, como testar e quais camadas foram de fato verificadas: validação offline, compilação, execução local ou multiplayer. Para desempenho, apresente a medição e as condições antes/depois; configuração reduzida ou cache limitado não equivale a ganho de FPS comprovado.
