# Validação v2

Executado em 10 de novembro de 2026 no ambiente de desenvolvimento Windows, sem reproduzir o computador GTX 1080 do parceiro.

## Concluído

- PE/PDB: GUID `18355a00-5500-48db-a06f-cfffd22e4dda`, age `1`, correspondentes.
- Símbolos consultados localmente com DbgHelp; desmontagem com dumpbin 14.51.36248.0.
- String `nod3dasync` lida por referência RIP-relative em `0x142f39c80`; chamada seguinte a `FParse::Param` e inversão do resultado conferidas.
- Desmontagem do arquivo alterado em cópia temporária: `xor eax,eax; ret; nop` no ponto previsto.
- Hash do arquivo alterado: `e816bd65e1e1fbf9b8367c3dd1510bc3337fd7f6d538a2e3090c398f87da2462`.
- 13 testes passaram, incluindo alteração apenas dos quatro bytes previstos, recusa de outra versão, aplicação repetida, backup corrompido, restauração byte a byte, preservação de configuração/codificação e execução das rotas de perfil no ZIP extraído.
- Coletor PowerShell v2 executado com sucesso em modo de diagnóstico; produziu ZIP local. Os dados coletados são do PC de referência, não do parceiro.
- O SHA-256 do executável instalado no PC de referência permaneceu igual ao original. O patch só foi aplicado em pastas temporárias de teste. Nenhum jogo foi iniciado nesta etapa v2.

## Sessão REA/Ghidra

A inspeção de diretório v1 foi concluída pelo REA e está descrita em `rea-provenance.json`.

Na v2, a primeira chamada do cliente local tinha limite padrão de 60 segundos devido ao uso incorreto da assinatura da versão instalada do SDK. O cliente foi corrigido para passar as opções no segundo argumento; a sessão foi fechada e o processo do provedor removido.

A tentativa seguinte recebeu `provider_timeout` após 900.000 ms de importação/análise automática. O servidor informou saída incompleta, não confirmou OutOfMemoryError e recomendou restringir analisadores ou ampliar o prazo. O fechamento foi concluído e o JVM do provedor deixou de existir. Não há pseudocódigo concluído atribuível a essa tentativa.

O perfil restrito desativou `WindowsResourceReference`, `Non-Returning Functions - Discovered` e `Decompiler Switch Analysis`, com prazo de 300.000 ms e heap de 3 GB. A decisão foi baseada no diagnóstico de threads do JVM e nas mensagens de análise. Essas etapas omitidas limitam inferências sobre recursos, funções sem retorno e switches. Essa tentativa também recebeu `provider_timeout`; o diagnóstico de threads mostrava a etapa global de desmontagem dos pontos de entrada. O fechamento terminou e nenhum JVM dessas sessões permaneceu ativo. Não foi produzido pseudocódigo completo pelo REA/Ghidra nesta rodada.

Os achados e o patch v2 estão, portanto, sustentados pela desmontagem com dumpbin e pelos símbolos correspondentes do PDB. O resultado da tentativa de decompilação é registrado separadamente em `native-provenance.json`; não foi convertido em uma alegação de análise bem-sucedida.

## Não validado

Não houve execução do binário modificado, teste de chegada ao menu na GTX 1080, medição de FPS, captura de argumentos no computador afetado ou confirmação da causa do crash. Testes de edição e restauração não comprovam estabilidade gráfica. A opção `-nod3dasync` e o patch equivalente permanecem mitigações experimentais.

As configurações atuais do PC de referência diferem do backup da sessão v1; não foram restauradas novamente nem alteradas na v2, preservando mudanças posteriores do usuário.
