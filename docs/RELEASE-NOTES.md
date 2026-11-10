# ForgeLoader 0.2.0-alpha

Esta versão carrega mods Lua e DLL x64 no jogo. Atualize o pacote **ForgeLoader para jogadores**, instale um arquivo **.flmod** pelo botão **Instalar mod** ou por **ForgeLoader/Instalar-Mod.cmd**, e reinicie o jogo. **Meus mods** mostra os mods carregados e seus erros.

Downloads separados: pacote para jogadores, Dev Kit e três exemplos `.flmod` (título, limite de FPS e DLL). O pacote para jogadores também inclui os dois exemplos Lua para instalação opcional. Não distribui o jogo nem exige Python/Lua no PC de quem joga.

Os três exemplos foram executados no jogo local. Foram verificados o título da janela, callback Lua, callback nativo e limite de FPS com leitura de confirmação do motor. 32 testes Python/PowerShell passaram, além dos testes nativos de protocolo, imagens e execução Lua/DLL.

A captura automática da janela falhou; aparência e cliques do painel não foram validados automaticamente. O importador de fotos existente foi preservado. Negociação no lobby e mods de simulação compartilhada ainda não estão implementados; esta versão aceita mods locais. Recepção de fotos entre PCs, ganho de FPS e correção do crash da GTX 1080 não estão confirmados.

O Dev Kit foi atualizado com a API implementada, gerador, empacotador e instruções para IA. Os exemplos antigos de UE4SS exigem portabilidade. Compatibilidade limitada ao build 0.253 identificado no perfil; há verificação de hash, backup, atualização do runtime v3 e restauração.
