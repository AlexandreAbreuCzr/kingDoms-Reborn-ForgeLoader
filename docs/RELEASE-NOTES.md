# ForgeLoader 0.2.2-KR214

Corrige o crash ao carregar um retrato personalizado durante a sincronização do lobby. Em uma cópia do jogo, o hook criou e reutilizou uma textura de foto válida e manteve o retrato padrão com uma imagem inválida. A sincronização entre dois PCs ainda precisa de teste.

Atualização para **Kingdoms Reborn 0.214**. Inclui o seletor de `.flmod` vinculado à janela do jogo, instalação verificada na pasta `Mods/`, perfil leve GTX 1080 opcional e reparador de saves com seleção explícita do doador. Atualiza os runtimes KR214 conhecidos com backup; o pacote para 0.253 é separado.

- **Jogar:** extraia o ZIP para jogadores, feche o jogo e execute `Instalar-ForgeLoader.cmd`.
- **Desempenho:** instale `forge.kr214_performance-1.0.0.flmod` e reinicie. O perfil limita resolução 3D a 85%, reduz sombras e desativa efeitos gráficos selecionados.
- **Rejoin:** mantenha o `yongs.rejoin_fix` original em `Mods/`; a DLL do amigo não está incluída nesta publicação.
- **Saves:** abra `ForgeLoader/Reparar-Save.cmd` e escolha o save afetado e um anterior do mesmo mundo. A ferramenta requer Python 3.10+ e cria uma cópia, sem converter versões.

No teste local, o jogo abriu com o perfil e rejoin 1.2.0 carregados; o motor confirmou os valores gráficos. A abertura do seletor foi confirmada pelo usuário. Reparação em cópia e recusas de doadores incompatíveis foram testadas. Reconexão entre PCs e desempenho na GTX 1080 ainda não foram medidos.

O ZIP não inclui o jogo. Confira `KR214.md` e os hashes dos arquivos da publicação.
