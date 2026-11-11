# Instalar ForgeLoader para Kingdoms Reborn 0.214

Extraia o ZIP, feche o jogo e abra **Instalar-ForgeLoader.cmd**. Selecione a pasta da versão 0.214 que contém `PunCity`. O instalador verifica os arquivos e guarda o estado anterior em `ForgeLoader/Backups`.

**Instalar um mod:** clique em **Instalar mod** no jogo ou abra `ForgeLoader/Instalar-Mod.cmd` na pasta do jogo. Escolha um `.flmod`, reinicie e confira em **Meus mods**. Para copiar manualmente, coloque a pasta descompactada em `Mods/autor.nome`, com `mod.json` diretamente dentro dela.

**Perfil leve:** selecione `mods-exemplo/forge.kr214_performance-1.0.0.flmod`. Ajusta resolução 3D, sombras e efeitos no processo, sem alterar saves. Use apenas um mod de limite de FPS por vez.

**Saves:** `ForgeLoader/Reparar-Save.cmd` abre o seletor de save afetado e doador anterior do mesmo mundo. Requer Python 3.10+ com Tkinter. Cria uma cópia `Reparado-...`; não converte saves da versão 0.253. Leia `KR214.md` para os requisitos.

**Rejoin:** preserve o `.flmod` original `yongs.rejoin_fix` do seu amigo. Se já estiver em `Mods`, será carregado pelo runtime compatível. O carregamento foi verificado; reconexão entre PCs ainda precisa de teste.

Para reverter a instalação, feche o jogo e abra **Restaurar-Backup.cmd**. Isso restaura a versão anterior do EXE/runtime, inclusive se já havia um loader instalado. O perfil leve é opcional; para desativar, mova sua pasta para fora de `Mods` com o jogo fechado.
