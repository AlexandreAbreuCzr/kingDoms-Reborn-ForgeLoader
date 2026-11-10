# Kingdoms Reborn — retratos v3 experimentais

Este pacote contém um EXE real modificado e `KingdomsPortraits.dll`. É um protótipo para a versão exata fornecida neste projeto. Ainda não há validação visual completa nem teste entre dois computadores. Não é uma correção confirmada para o crash da GTX 1080.

Desde a v2, o pacote não inclui o patch NoAsync que estava misturado à primeira versão. A política gráfica usa o comportamento original do engine. A v1 apresentou perda do dispositivo D3D11 na RX 7600 e foi retirada de uso. Esse resultado não demonstra sozinho que NoAsync causou a falha. Atualize EXE e DLL juntos.

A v3 mantém a política gráfica da v2 e corrige o painel ausente na tela Configurações do Líder: acompanha a abertura dessa tela pelo ciclo do lobby e usa uma janela nativa pertencente ao jogo, posicionada sobre sua área interna. Não é um widget UMG/Blueprint. A aplicação e a remoção da foto também passam pelo ciclo do lobby e atualizam a prévia usada pelo botão Finalizado.

## Preparar uma cópia de teste

1. Feche o jogo. Use uma cópia da pasta completa do jogo, separada da instalação de uso normal. O ZIP contém somente os arquivos alterados, não o jogo completo.
2. Guarde o EXE original de `PunCity\Binaries\Win64\PrototypeCity-Win64-Shipping.exe` fora da pasta de teste.
3. Guarde também uma cópia de `%LOCALAPPDATA%\PunCity\Saved\PlayerInfo.dat` e da pasta `GameSaves`. A cópia do jogo continua usando os dados deste mesmo usuário do Windows.
4. Extraia o conteúdo de `PunCity` deste pacote sobre a cópia do jogo. O novo EXE e `KingdomsPortraits.dll` devem ficar juntos em `PunCity\Binaries\Win64`.
5. Abra o Steam e depois o jogo da cópia de teste. Use modo janela ou janela sem bordas para o painel nativo do Windows. A tela cheia exclusiva ainda não foi validada.

O módulo só instala seus hooks no hash exato do EXE deste pacote. Não serve para atualizações futuras. Não precisa instalar Python, compilador, REA ou um servidor de fotos no PC do jogador.

## Importar e compartilhar

No lobby, abra **Configurações do Líder** (a tela com Facção, Ícone, Cor e Retrato). A v3 foi preparada para mostrar **Importar foto** e **Remover foto** no canto inferior esquerdo da área do jogo enquanto essa tela estiver aberta. O painel acompanha a janela, fica oculto quando você muda para outro aplicativo ou minimiza o jogo e não tem processo separado. A seleção usa a janela de arquivos do Windows, aberta pelo botão.

Selecione PNG/JPG de até 20 MB e 8192 pixels por lado. A imagem é recortada ao centro e convertida para JPEG de 128 × 128 pixels, com até 8 KiB. Ao confirmar, a imagem é colocada na fila de atualização do retrato. O nome do arquivo e seu caminho local não fazem parte do pacote enviado.

O transporte implementado reutiliza o RPC de informações do jogador e o campo `portraitName`. O módulo receptor decodifica a imagem e troca a textura do retrato. **A entrega, os limites do RPC real, quem entra depois e a persistência em saves ainda precisam de teste em dois clientes.** Um teste de codificação local não substitui esse teste.

Todos os participantes, incluindo o anfitrião, precisam deste mesmo EXE e DLL. Teste em um lobby privado novo com essas cópias. Clientes sem o mod não entendem o retrato personalizado. Evite gravar partidas de uso normal durante a validação.

**O aviso não pede que todos baixem sua foto.** Você escolhe a imagem uma vez no seu PC; o código foi preparado para levar os bytes pela própria partida e exibir o retrato nos outros clientes compatíveis. Os demais precisam do jogo com este recurso instalado, sem copiar ou importar manualmente a imagem. A recepção em outro PC ainda não foi validada.

O mod altera o retrato, sem criar um novo imperador com atributos próprios. A integração inicial cobre as rotinas de informações do personagem e retratos no lobby. Outras telas e versões ainda não foram validadas.

## Remover

Use **Remover foto** no lobby para solicitar a restauração do retrato original pelo RPC. Como esse fluxo também aguarda validação no jogo, mantenha o backup.

Feche o jogo. Restaure o EXE original e o `PlayerInfo.dat` guardado antes do teste; remova somente a DLL adicionada por este pacote. Se tiver criado saves de teste com retratos personalizados, mantenha-os separados das partidas abertas no jogo original. Não apague toda a pasta `Saved`.

## Verificado e pendente

Passaram na v3 a compilação x64, os testes de protocolo e regras de visibilidade, a importação real de PNG pelo GDI+, a normalização para JPEG e a decodificação local de recebimento. O teste PE confirma preservação das 42 entradas de importação e de todas as seções originais do EXE. Após reiniciar com v3, o usuário abriu o importador; o log registrou decodificação de textura, chamada de envio e chamada de restauração durante seu teste local.

Não foram confirmados: resultado visual final do retrato, recepção/restauração em outro cliente, entrada tardia, compatibilidade com saves ou resolução do crash D3D11 no PC do parceiro. O usuário esclareceu que testou sozinho, sem estar numa partida com o parceiro.

O processamento de fotos tem limites de tamanho e cache, mas não houve benchmark do jogo. Não há ganho de FPS comprovado nem otimização geral concluída.

O log fica em `%LOCALAPPDATA%\PunCity\Saved\PortraitMod\runtime.log`. Registra eventos sem fotos, caminhos dos arquivos selecionados ou identificadores de conta. Não há envio automático de diagnósticos. `manifest.json` contém os hashes do pacote.

## Desenvolvimento

Fontes em `native/portraits`; scripts de geração em `scripts`. MinHook 1.3.4 é usado sob a licença incluída em `LICENSE-MINHOOK.txt`. O EXE preserva autenticação, RPCs e código gráfico originais. Para gerar a v2 use `python scripts/build_portrait_exe.py --source CAMINHO_DO_EXE_ORIGINAL`; o gerador recusa um EXE já modificado.
