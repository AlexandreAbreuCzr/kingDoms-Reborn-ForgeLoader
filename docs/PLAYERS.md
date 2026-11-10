# ForgeLoader — quero jogar

Este pacote instala o **runtime de retratos v3** na sua cópia de Kingdoms Reborn. O carregador geral de mods Lua/C++ ainda está em desenvolvimento. Ele não inclui o jogo completo.

## Instalar

1. Extraia todo o ZIP para uma pasta.
2. Feche o jogo e dê dois cliques em **Instalar-ForgeLoader.cmd**.
3. Escolha a pasta do Kingdoms Reborn que contém `KingdomsReborn.exe` e `PunCity`.
4. Aguarde a mensagem de conclusão e abra o jogo normalmente.

O instalador confere a versão antes de alterar arquivos e guarda backup em `ForgeLoader/Backups`, dentro da pasta do jogo. Não precisa instalar Python, compilador ou Dev Kit para jogar. Uma versão diferente ou DLL desconhecida é recusada.

## Colocar uma foto

No lobby, abra **Configurações do Líder**. Use **Importar foto** no canto inferior esquerdo e escolha PNG/JPG. Confirme e finalize a configuração do líder. **Remover foto** solicita a volta ao retrato anterior.

Você importa a foto uma vez. O código foi feito para transmiti-la pela partida; os demais jogadores precisam do mesmo runtime, sem baixar ou importar a imagem manualmente. A recepção entre dois PCs ainda aguarda validação. A foto é recortada ao centro para 128 × 128 pixels e até 8 KiB.

O painel usa uma janela nativa pertencente ao jogo. Prefira modo janela ou janela sem bordas. Tela cheia exclusiva ainda não foi validada.

## Restaurar

Feche o jogo, abra **Restaurar-Backup.cmd** e escolha a mesma pasta. Ele restaura o estado anterior à instalação, incluindo `PlayerInfo.dat`, e preserva uma cópia do estado atual antes de restaurar. Saves de cidades não são alterados. Mantenha saves criados durante testes separados de suas partidas normais.

Se você instalou uma versão antiga manualmente, use o backup que guardou naquela instalação. O instalador só restaura backups criados por ele e recusa arquivos alterados depois.

## O que este alpha oferece

- Inicialização e importação local de fotos executadas no PC de referência.
- Backup, validação de versão e restauração do instalador testados em cópias temporárias.
- Nenhum carregamento automático de arquivos da pasta `Mods` nesta versão.
- Nenhum ganho de FPS medido ou correção confirmada para a GTX 1080.

Estado completo em `STATUS.md`. Relate falhas pela página Issues, informando a versão e o que aconteceu; não é necessário enviar saves ou dumps completos para um relato inicial.
