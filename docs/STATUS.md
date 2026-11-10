# Estado do ForgeLoader 0.2.0-alpha

| Recurso | Estado |
| --- | --- |
| Instalador do loader, atualização do v3, backup e restauração | Implementados e testados |
| Instalação de pacotes .flmod e pasta Mods | Implementada e testada |
| Carregamento de mods Lua e DLL x64 | Implementado; três exemplos executados no jogo local |
| API de logs, título, FPS e eventos | Integrada à thread do jogo; exemplos executados |
| Dependências, conflitos, ciclos, erros por mod | Implementados; testes nativos |
| Painel Meus mods / Abrir pasta / Instalar mod | Criado no jogo; captura automática indisponível neste teste |
| Dev Kit e instruções de IA | Atualizados para a API integrada |
| Importador de retratos | Protótipo preservado; importação local validada anteriormente |
| Fotos automáticas entre PCs e entrada tardia | Recepção remota ainda não validada |
| Negociação no lobby e simulação compartilhada | Não implementadas; mods required recusados |
| Acesso Lua genérico a todos os objetos Unreal | Não implementado |
| Ganho de FPS / correção para GTX 1080 | Não confirmado |

[Detalhes da validação](VALIDATION-0.2.0.md). O runtime aceita somente o build identificado e mods locais. Os testes do CI não incluem execução do jogo. O limite de FPS não é uma medição de ganho de desempenho.
