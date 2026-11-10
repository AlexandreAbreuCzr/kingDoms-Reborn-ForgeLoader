# Estado do ForgeLoader 0.1.0-alpha

| Recurso | Estado |
| --- | --- |
| Instalador para a cópia existente do jogo | Implementado, com hash e backup |
| Runtime nativo de retratos v3 | Importação local executada |
| Envio pelo RPC existente | Chamada local executada; recepção remota não validada |
| Fotos automáticas entre PCs e entrada tardia | Pendente de teste |
| Gerador de projetos e exemplos Lua/C++ | Disponíveis no Dev Kit |
| Verificação de dependências e arquivos | Implementada fora do jogo |
| Carregador geral de mods | Em desenvolvimento; não implementado |
| API Lua/C++ integrada ao jogo | Não implementada |
| Checagem de mods no lobby | Não implementada |
| Ganho de FPS / correção para GTX 1080 | Não confirmado |

O nome ForgeLoader representa o projeto em construção. O download atual para jogadores oferece o runtime de retratos; colocar um script ou DLL adicional na pasta do jogo ainda não o transforma em um mod carregado.

Os testes automatizados de configuração e instalador usam pastas temporárias. Testes que precisam do EXE original são pulados quando esse arquivo não é fornecido. Uma execução de CI sem o jogo não comprova estabilidade, renderização ou compatibilidade multiplayer.
