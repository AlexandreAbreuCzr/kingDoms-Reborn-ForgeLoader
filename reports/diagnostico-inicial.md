# Kingdoms Reborn: diagnóstico inicial

Este arquivo registra o estágio v1. O usuário posteriormente informou que os ajustes não resolveram o crash; os achados e o patch experimental posteriores estão em `analise-binaria-v2.md`.

Data: 10 de novembro de 2026. Alvo informado: **PC do parceiro, GeForce GTX 1080 normal e Windows 11 atualizado**. Versão exata do Windows, driver NVIDIA, RAM, configurações, eventos e novos dumps desse computador ainda não foram recebidos. O PC que contém os arquivos funciona normalmente segundo o usuário; seus dados não representam o computador afetado.

## Falha prioritária

A imagem e a pilha fornecidas mostram `0x887A0020`, `INTERNAL_ERROR`, enquanto o Unreal cria uma textura D3D11 em `SafeCreateTexture2D`, durante a abertura, antes do menu. A Microsoft define esse código como `DXGI_ERROR_DRIVER_INTERNAL_ERROR`: o driver encontrou um problema e o dispositivo entrou no estado de removido. Isso não identifica sozinho a causa original, não comprova falta de VRAM e não estabelece defeito físico na GPU. A pilha de CPU indica onde a falha foi detectada, não necessariamente o comando que a provocou.

O erro já está no caminho DirectX 11. Acrescentar `-dx11` isoladamente não troca o renderizador que falhou. A presença de strings D3D12/Vulkan no executável não confirma shaders compatíveis; esses renderizadores não são forçados neste pacote.

Fonte: [Microsoft — DXGI_ERROR](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/dxgi-error).

## Evidências obtidas dos arquivos fornecidos

O REA 6.8.0 inspecionou 132 entradas da instalação, examinou cabeçalhos de 40 arquivos e leu 13.584 bytes nessa inspeção. Identificou estrutura de conteúdo Unreal. Essa inspeção não executa o jogo e seu digest de diretório não representa o hash integral de todos os arquivos. Evidências completas e resumo estão retidos localmente no projeto, fora do pacote portátil.

A comparação independente com o ZIP fornecido validou o CRC do ZIP e o SHA-256 dos seguintes arquivos contra a pasta extraída:

| Arquivo | SHA-256 | Resultado |
| --- | --- | --- |
| KingdomsReborn.exe | `086b71bebb78d3748c0ea67485cc28d4befb1cdbc30a31118c2952a1bd8d0512` | Igual ao ZIP |
| PrototypeCity-Win64-Shipping.exe | `8f2653ba07d53c3e01eb68a3f0a9a5851ef96e84d42181a5dd7a279740d0033c` | Igual ao ZIP |
| PunCity-WindowsNoEditor.pak | `603d4d16369f3fb3ee8f69215c11f5a6051da1ceb176686917362ca11c86b9fc` | Igual ao ZIP |

Isso afasta uma diferença de extração nesses arquivos. Não autentica a distribuição nem valida a instalação existente no PC do parceiro.

O executável PE x64 importa `d3d11.dll` e `dxgi.dll`. Foram encontrados literalmente `t.MaxFPS`, `r.Streaming.LimitPoolSizeToVRAM`, `r.Streaming.PoolSize`, `r.TextureStreaming`, `r.RHICmdBypass` e `norhithread`. A presença de uma string não comprova execução ou eficácia de uma opção.

Existe um PDB fornecido junto ao executável. Não foi validada a correspondência GUID/age do PDB e não foi realizada decompilação. O REA informou que Ghidra, IDA e Kuna não estão configurados; Hopper não está disponível neste host Windows. Não foi instalado um descompilador adicional.

O único crash encontrado no PC de referência registra Unreal Engine **4.25.4** e uma violação de acesso em `SWindow::GetClientRectInScreen` / `FDefaultGameMoviePlayer::PlayMovie`, no carregamento inicial. É outra falha, em outra máquina, e não deve ser confundida com a perda do dispositivo D3D11 da imagem. A versão do engine vem desse crash local; a correspondência com a instalação atual permanece não verificada.

## GTX 1080 e driver

A GTX 1080 pertence à geração Pascal. A NVIDIA informou que Maxwell, Pascal e Volta passaram a receber apenas atualizações críticas de segurança a partir de outubro de 2025, com suporte desse tipo previsto até outubro de 2028. Portanto, a investigação deve usar um driver que liste explicitamente a GTX 1080 e Windows 11; “Game Ready mais recente” sem verificar a lista não é uma orientação suficiente. Ainda não sabemos o driver instalado no computador afetado. Nenhum driver foi instalado ou removido.

Fonte: [NVIDIA — plano de suporte Maxwell/Pascal/Volta](https://nvidia.custhelp.com/app/answers/detail/a_id/5676/).

## Hipóteses e testes

| Hipótese | O que sabemos | Próxima verificação |
| --- | --- | --- |
| Interação do driver NVIDIA com criação de texturas D3D11 | Compatível com o código de erro; causa não demonstrada | Driver, eventos de reset e crash do PC afetado |
| Configuração gráfica ou modo de janela | Ainda não recebidos desse PC | Perfil reversível 720p em janela, 45 FPS, qualidade reduzida |
| Caminho de renderização com thread RHI separada | Opção `norhithread` presente no binário | Segundo teste separado, somente se o primeiro falhar |
| Arquivos diferentes na máquina do parceiro | Arquivos locais correspondem ao ZIP; PC afetado não inspecionado | Comparar SHA-256 dos dois executáveis coletados |
| Instabilidade, clocks ou pressão de memória da GPU | Não medida; erro não comprova nenhuma dessas causas | Cruzar eventos e driver antes de propor mudanças no sistema |

## Entrega e limites

O pacote portátil contém ferramentas PowerShell, um perfil JSON comum, iniciadores CMD e instruções. Não contém o jogo, DLLs, REA executável, saves, dumps ou configurações pessoais do PC de referência. O REA e os cinco submódulos permanecem no projeto de análise. Binwalk/Unblob são voltados a firmware, JADX a Android, Wakaru a JavaScript e a extensão NativeAOT a outro tipo de binário; executá-los indiscriminadamente não oferece uma correção para este alvo Unreal PE.

O perfil é uma **mitigação candidata**, não um patch do jogo nem uma correção comprovada. A variante de compatibilidade usa `-norhithread` e pode reduzir o desempenho. Nenhum ganho de FPS foi medido. O coletor registra dados locais, mas não confirma visualmente se o menu respondeu.

Os testes automatizados verificam preservação de configuração, codificação, aplicação repetida, bloqueio com jogo aberto e restauração, incluindo backup corrompido e regravação pelo jogo. Foram executados em pastas temporárias; não substituem o teste na GTX 1080.

Antes da identificação correta da máquina afetada, foi iniciado um teste no PC de referência. A primeira abertura exibiu “Steam Error” e abriu o Steam; a segunda manteve o processo do jogo, sem novo contexto de crash na janela monitorada de 120 segundos. A captura visual não respondeu e o menu não foi confirmado. O teste foi encerrado e os dois INIs foram restaurados byte a byte aos backups anteriores. Isso não valida a correção no computador do parceiro.

O próximo dado necessário é o ZIP de diagnóstico gerado no PC afetado, primeiro antes de aplicar ajustes e depois após cada tentativa, acompanhado da informação de chegada ao menu e ocorrência do mesmo erro.
