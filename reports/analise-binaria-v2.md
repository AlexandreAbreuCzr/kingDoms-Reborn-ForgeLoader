# Análise binária v2 — inicialização D3D11

10 de novembro de 2026. O usuário informou que os ajustes do pacote v1 não resolveram o crash no PC do parceiro, com GTX 1080 e Windows 11. Ainda não foram recebidos logs, driver ou dump desse computador. Portanto, os resultados abaixo são análise do binário fornecido e uma mitigação experimental, **não uma causa confirmada nem uma correção validada do crash**.

## Identidade e ferramentas

O executável analisado tem SHA-256 `8f2653ba07d53c3e01eb68a3f0a9a5851ef96e84d42181a5dd7a279740d0033c`. O registro CodeView RSDS do PE e o stream de identificação do PDB concordam no GUID `18355a00-5500-48db-a06f-cfffd22e4dda` e age `1`.

Os símbolos foram consultados localmente com DbgHelp, sem executar o jogo nem acessar um servidor de símbolos. A desmontagem foi realizada com o `dumpbin` do Visual Studio instalado. Esses resultados são evidências dessas ferramentas, não devem ser atribuídos ao REA. O REA continua responsável pela inspeção anterior e pela sessão de análise nativa descrita no arquivo de validação do projeto.

O Ghidra 12.1.4 foi obtido do [repositório oficial da NSA](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build), com SHA-256 do arquivo ZIP `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db` conferido contra o digest da publicação. A distribuição fica local ao projeto, sem registro global ou instalação no computador do parceiro.

## O que o código demonstra

| Símbolo/caminho | Endereço virtual preferido | Evidência |
| --- | --- | --- |
| `SafeCreateTexture2D` D3D11 | `0x142f51710` | Chama `ID3D11Device::CreateTexture2D` por vtable; em HRESULT negativo chama o verificador |
| `VerifyD3D11CreateTextureResult` | `0x142f53560` | Encaminha falha ao tratamento de perda de dispositivo, antes de montar a mensagem completa de textura |
| Tratamento de perda de dispositivo | `0x142f526c0` | Quando recebe `DXGI_ERROR_DEVICE_REMOVED`, consulta o motivo com `GetDeviceRemovedReason` e termina por erro fatal |
| `D3D11RHI_ShouldAllowAsyncResourceCreation` | `0x142f39c30` | Retorna a negação de `FParse::Param(FCommandLine::Get(), L"nod3dasync")`, guardada em estático |
| `FD3D11DynamicRHI::InitD3DDevice` | `0x142f3e4c0` | Usa essa decisão na montagem dos flags de criação do dispositivo |
| `FD3D11DynamicRHI::RHICreateTexture2D_RenderThread` | `0x142f47a40` | Encaminha a criação ao helper de texturas D3D11 |

Os endereços acima são VAs preferidos do arquivo; ASLR pode alterar o endereço em execução. Há duas funções com o nome `SafeCreateTexture2D` no PDB; a segunda pertence ao outro caminho de renderização. A análise foi direcionada à variante D3D11 da pilha enviada.

A instrução em `0x142f39c80` referencia a string UTF-16LE `nod3dasync` em `0x145036928`. O código chama `FParse::Param`, testa seu retorno e grava o resultado invertido. Reconstrução manual do comportamento observado:

```cpp
bool D3D11RHI_ShouldAllowAsyncResourceCreation() {
    static bool allow = !FParse::Param(FCommandLine::Get(), L"nod3dasync");
    return allow;
}
```

Essa reconstrução foi feita da desmontagem com símbolos. Não é o código-fonte original do jogo.

Na inicialização, o retorno falso habilita o bit `1` no conjunto de flags do dispositivo. Para o caminho NVIDIA observado, o valor é encaminhado à criação D3D11. Há um ramo específico AMD que pode limpar esse bit, reforçando que um resultado na RX 7600 do PC de referência não comprovaria o comportamento na GTX 1080. Entre `0x142f3ef8c` e `0x142f3efae`, o código testa as capacidades de criação concorrente do driver e o bit `1` dos flags; quando esse bit está ligado, grava falso em `GRHISupportsAsyncTextureCreation`.

O bit `1` é `D3D11_CREATE_DEVICE_SINGLETHREADED`, segundo a [documentação da Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/d3d11/ne-d3d11-d3d11_create_device_flag). A aplicação deve respeitar as exigências desse modo; neste projeto usa-se a seleção que o próprio engine já implementa, sem inventar sincronização nova.

`-norhithread`, do pacote v1, é uma escolha diferente: não equivale a desabilitar a criação assíncrona de recursos D3D11. A opção encontrada fornece um teste mais específico, embora ainda não demonstre que o caminho assíncrono está defeituoso.

## Significado exato da mensagem de crash

No tratamento em `0x142f526c0`, a comparação inicial é com `0x887A0005`, `DXGI_ERROR_DEVICE_REMOVED`. Depois há uma chamada ao método na posição `0x138` da vtable do dispositivo, `GetDeviceRemovedReason`. O valor retornado é comparado, entre outros, com `0x887A0020`; nesse caso a mensagem escolhe `INTERNAL_ERROR`. A chamada do erro fatal contém a linha `0xC6`, ou 198, correspondente à captura enviada.

Esse caminho coincide com a mensagem e a linha da captura. A identidade do build no PC do parceiro ainda precisa ser conferida pelo hash. **O código 0x887A0020 da mensagem não precisa ser o HRESULT original retornado por CreateTexture2D**: é o motivo de remoção consultado depois. Não identifica a textura defeituosa, uma condição de concorrência ou um defeito físico na GPU.

O comportamento assíncrono da GPU também limita a interpretação da pilha de CPU: o comando causador pode ser anterior ao ponto de detecção. A [documentação da Epic sobre crashes de GPU](https://dev.epicgames.com/documentation/en-us/unreal-engine/dealing-with-a-gpu-crash-when-using-unreal-engine) explica essa limitação. A documentação atual é do Unreal 5; foi usada para o princípio de diagnóstico, não para supor que ferramentas específicas do UE5 existam neste build UE4.

## Teste e patch candidatos

O comando **5-Testar-D3D11-Sem-Async.cmd** inicia o jogo com `-nod3dasync`, preservando o executável. É o primeiro teste recomendado para esta hipótese.

O comando **6-Aplicar-Patch-Binario-NoAsync.cmd** é uma alternativa opcional para fixar a seleção independentemente dos argumentos do iniciador. Ele só aceita a versão exata analisada e altera quatro bytes na entrada da função:

| Campo | Valor |
| --- | --- |
| Offset no arquivo | `0x2f39230` (49.517.104) |
| Bytes originais | `48 83 EC 28` — `sub rsp, 0x28` |
| Bytes alterados | `33 C0 C3 90` — `xor eax,eax; ret; nop` |
| SHA-256 do resultado | `e816bd65e1e1fbf9b8367c3dd1510bc3337fd7f6d538a2e3090c398f87da2462` |

O helper passa a retornar falso desde a entrada, sem executar o corpo original nem alterar a pilha. O patch não altera `SafeCreateTexture2D`, seus verificadores, o retorno das APIs, o tratamento fatal ou a proteção de perda do dispositivo. Não mexe em Steam, licenciamento, autenticação ou DLLs.

O patch e a opção 5 selecionam o mesmo resultado nessa função. **Se `-nod3dasync` foi comprovadamente aplicado e não resolveu, aplicar esse patch não constitui outra hipótese de correção.** Não se deve prometer que um dos dois resolverá o problema sem teste na máquina afetada.

O backup completo é gravado e verificado antes da substituição. A substituição usa arquivo temporário e troca atômica. Uma versão diferente é recusada. O comando **7-Restaurar-Executavel-Original.cmd** só restaura quando o executável atual é o resultado esperado do patch e o backup original tem o hash correto; uma atualização ou alteração posterior é preservada mediante recusa da restauração automática.

O pacote não inclui o executável do jogo. O patch foi aplicado e revertido apenas em cópias temporárias de teste, sem executar essas cópias. O jogo instalado no PC de referência não foi alterado nesta investigação.

## O que falta para chamar isto de correção

Falta identificar a operação causadora no PC afetado e verificar se o mesmo crash persiste com a nova seleção. São necessários o resultado do teste e o diagnóstico local: hash do executável, driver NVIDIA, versão exata do Windows, contexto de crash e eventos de reset. Não foi identificado até aqui um erro comprovado no código do jogo que explique sozinho a falha da GTX 1080.
