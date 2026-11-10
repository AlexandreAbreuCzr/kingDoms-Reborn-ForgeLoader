# Instalar o ForgeLoader e seus mods

1. Extraia **ForgeLoader-Players-0.2.0-alpha.zip**.
2. Feche o jogo, abra **Instalar-ForgeLoader.cmd** e escolha a pasta que contém `PunCity`.
3. Baixe um mod `.flmod`, ou use os arquivos na pasta **mods-exemplo** do pacote.
4. Abra o jogo e clique em **Instalar mod**, no painel superior direito. Selecione o `.flmod`.
5. Reinicie o jogo. **Meus mods** mostra os mods carregados e os erros.

Se preferir instalar com o jogo fechado, abra **ForgeLoader/Instalar-Mod.cmd** dentro da pasta do jogo. O instalador abre um seletor de arquivos. A versão antiga 0.1 não carrega mods: atualize o pacote para jogadores primeiro. Não precisa do Dev Kit, Python ou Lua instalado.

## Pasta dos mods

Um mod descompactado tem esta estrutura:

```text
Kingdoms Reborn/
  Mods/
    autor.meumod/
      mod.json
      Scripts/main.lua
```

Você pode copiar essa pasta manualmente. Um `.flmod` é um ZIP com `mod.json` na raiz; instale pelo seletor ou extraia em uma pasta própria. Não coloque o ZIP inteiro ou uma pasta dentro de outra pasta do mesmo mod. Mods `.jar` de Minecraft e projetos de UE4SS não usam a API deste loader.

Para atualizar um mod, feche o jogo e mova sua pasta antiga para fora de Mods antes de instalar a nova. O instalador preserva pastas existentes. Para desativar/remover, feche o jogo e mova a pasta do mod para fora de Mods. Alterações são lidas ao iniciar.

**Exemplos:** forge.hello altera o título da janela; forge.fps_limit aplica limite de 60 FPS na sessão; forge.native_hello escreve uma mensagem pelo módulo C++. No FPS, edite `settings.fps` do `mod.json` com o jogo fechado (0 = sem limite, ou 15–240). Nenhum deles altera regras da partida.

## Fotos

No lobby, abra **Configurações do Líder**, use **Importar foto**, escolha PNG/JPG, confirme e finalize. **Remover foto** restaura o retrato. A imagem é recortada para 128 × 128 e até 8 KiB. O código envia a foto pela partida; cada participante precisa do runtime compatível, sem copiar a imagem manualmente. A recepção entre PCs ainda precisa de validação real.

Use janela ou janela sem bordas para os painéis nativos. Tela cheia exclusiva não foi validada.

## Backup e diagnóstico

O instalador verifica o build e preserva backup em `ForgeLoader/Backups`. Com o jogo fechado, **Restaurar-Backup.cmd** restaura o estado anterior à última instalação e o perfil de retrato, preservando uma cópia do estado atual. Saves de cidades não são alterados. Ele não remove suas pastas de mods.

**Meus mods** mostra erros. O relatório fica em `%LOCALAPPDATA%\PunCity\Saved\ForgeLoader\mods-status.json` e o log em `runtime.log` na mesma pasta. Mods locais são suportados; mods de simulação `required` são recusados até existir negociação multiplayer. Não há ganho de FPS medido ou correção confirmada para GTX 1080.
