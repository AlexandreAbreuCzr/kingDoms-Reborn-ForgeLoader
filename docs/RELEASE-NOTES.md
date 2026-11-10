# ForgeLoader 0.1.0-alpha

Dois downloads separados:

- **ForgeLoader-Players-0.1.0-alpha.zip**: extraia e abra `Instalar-ForgeLoader.cmd`. Escolha a pasta da sua cópia do jogo. O instalador verifica o build, aplica o runtime de retratos v3 e guarda backup. `Restaurar-Backup.cmd` volta ao estado anterior.
- **ForgeLoader-DevKit-0.1.0-alpha.zip**: extraia e abra `Abrir-DevKit.cmd` para criar um projeto ou conferir exemplos. Requer Python 3.10+ para desenvolvimento.

O pacote para jogadores inclui a DLL do runtime e um patch pequeno aplicado localmente. Não inclui o jogo completo ou um EXE do jogo. Não precisa instalar Python ou o Dev Kit para jogar.

## Estado deste alpha

Importação local de fotos executada, com normalização para 128 × 128 e até 8 KiB. O código foi preparado para enviar a imagem pela partida sem cópia manual por cada participante. Recepção entre PCs ainda não foi validada.

O carregador geral de mods, a API integrada Lua/C++ e a checagem no lobby **ainda estão em desenvolvimento**. Os exemplos do Dev Kit não são carregados pelo jogo atual só por colocá-los numa pasta. Não há ganho de FPS medido nem correção confirmada para a GTX 1080.

Testes locais cobrem validação de manifestos, dependências, empacotamento, instalação, restauração e preservação do EXE. Fontes nativas compilados com testes de protocolo, visibilidade e imagem. CI não executa o jogo.

`SHA256SUMS.txt` e `release-manifest.json` permitem conferir os downloads. Guias completos e o roadmap estão no repositório.
