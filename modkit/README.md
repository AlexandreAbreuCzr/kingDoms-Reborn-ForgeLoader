# ForgeLoader Dev Kit — fundação 0.1.0-alpha

Objetivo: uma plataforma comunitária para criar e compartilhar mods de Kingdoms Reborn, com API Lua/C++, catálogo de módulos, compatibilidade multiplayer e retratos compartilhados no pacote básico.

**Este primeiro artefato é um kit de desenvolvimento fora do jogo.** Cria projetos, valida manifestos/dependências, calcula fingerprints e compara perfis. Não carrega Lua/DLLs no jogo e não implementa negociação de compatibilidade no lobby. Os exemplos ainda não foram executados dentro de Kingdoms Reborn. Não foi instalada uma nova versão do runtime nem alterada sua sessão de jogo.

## O que funciona agora

- Criar modelo de mod Lua sem sobrescrever projetos existentes.
- Validar ID, API, versão do jogo, arquivo de entrada, dependências e conflitos.
- Ordenar dependências e detectar ciclos/IDs duplicados.
- Exportar perfil a partir do hash real do EXE e da DLL de retratos v3.
- Comparar versões e arquivos dos mods compartilhados; mods locais podem diferir.
- Manter fotos pessoais fora do fingerprint. Os clientes não precisam ter a mesma foto.

O comparador verifica igualdade declarada de pacotes. Não prova que um mod é determinístico, não fiscaliza se um mod marcado como local altera gameplay e não é um sistema anticheat. A integração futura deverá aplicar essa política no runtime e no início da partida.

## Usar as ferramentas

Python 3.10+ é necessário apenas neste protótipo de desenvolvimento. Execute da raiz deste repositório:

```powershell
python modkit/krmodkit.py new meuautor.meumod --name 'Meu primeiro mod' --output artifacts/MeuMod
python modkit/krmodkit.py validate modkit/examples/lua
python modkit/krmodkit.py profile --game-exe 'CAMINHO/PunCity/Binaries/Win64/PrototypeCity-Win64-Shipping.exe' --mods modkit/examples/lua --output artifacts/meu-perfil.json
python modkit/krmodkit.py compare artifacts/perfil-host.json artifacts/perfil-convidado.json
```

`new --required` marca um projeto que deve existir em todos os clientes. O padrão `local` serve para o exemplo de log; ao alterar regras/simulação, o autor deve marcar `required`. Um mod obrigatório não pode depender de um pacote marcado como local. As dependências usam versões exatas nesta primeira implementação; intervalos compatíveis ainda não foram implementados.

O gerador de perfil aceita somente o EXE de retratos v3 e sua DLL conhecidos. Atualizações futuras exigem outro adaptador validado. O perfil não contém dados de conta, nomes de jogadores, saves ou a foto selecionada. Não há upload automático de perfis.

Saídas: código 0 para sucesso/igualdade offline, 1 para arquivos inválidos, 2 para diferenças de compatibilidade. Igualdade offline não equivale a partida validada. Nenhum código de mod é executado pelo validador.

## Exemplos para estudar

| Exemplo | Demonstração | Situação |
| --- | --- | --- |
| `examples/lua/kr_hello` | Estrutura `Scripts/main.lua`, inicialização e log | Template validado; runtime pendente |
| `examples/lua/kr_observer` | Hook de evento Unreal e busca de GameInstance | Usa APIs documentadas do UE4SS; execução no jogo pendente |
| `examples/native/kr_native` | Entrada de módulo nativo C++ e ciclo Unreal | Fonte e CMake; requer SDK UE4SS, sem DLL compilada |
| `../native/portraits` | Integração nativa de fotos, prévia e RPC do jogo | Protótipo v3, importação local executada; rede pendente |

Os exemplos Lua seguem o formato do UE4SS, que é candidato à base de scripts. **Não copie ainda esses exemplos para sua instalação esperando que o EXE v3 os carregue:** a v3 atual carrega somente o módulo de retratos. A integração com UE4SS precisa ser testada separadamente, com versão fixada e identificação deste build.

Para o exemplo nativo, use um projeto pai que forneça o target `UE4SS`, adicione `kr_native` via CMake e siga a documentação do SDK. Depois de compilar para a versão fixada, coloque o binário em `dlls/main.dll` e transforme `manifest.template.json` em `mod.json`. O manifest de exemplo é uma proposta do ModKit, não um formato que o UE4SS já conheça. A tradução entre esses formatos está pendente.

## API ampla, com limites explícitos

A API pública deverá cobrir eventos de ciclo do jogo, objetos/propriedades refletidos, interface, dados de recursos/cartas/edifícios, configurações e canais de mensagens. Lua facilita criar e recarregar scripts. C++ permite implementar adaptadores para sistemas não refletidos e operações que precisam de desempenho. Cada sistema precisa de pontos de entrada mapeados e testes; não existe hoje uma promessa de que qualquer conteúdo ou algoritmo possa ser substituído.

O build disponível é Unreal 4.25.4, com EXE/PDB e assets empacotados. Não há projeto Unreal ou SDK oficial fornecido. Novos assets, Blueprints, modelos e mapas também exigem pipeline de produção/cooking compatível. Acesso nativo não resolve automaticamente esse pipeline.

## Fotos e desempenho como módulos básicos

`builtins.json` registra o desenho inicial. Retratos vêm habilitados no pacote básico, reaproveitando a v3 enquanto ela é separada do núcleo. A imagem deve trafegar automaticamente como dado limitado; não faz parte dos arquivos de código que os jogadores precisam igualar. Continua faltando teste real de recepção entre PCs, entrada tardia e saves.

Desempenho começa com diagnóstico e medição: mesmo save/câmera, tempo de frame, carregamento e memória antes/depois. Ajustes gráficos ficam em perfis locais; patches que afetam simulação exigem os mesmos módulos nos participantes. Não há ganho de FPS medido nem correção da GTX 1080 confirmada. NoAsync não é ativado pelo ModKit.

## Próximas entregas necessárias

1. Validar o carregador candidato em uma cópia controlada, com build/versão fixados e reversão.
2. Separar o runtime de retratos em módulo e estabelecer propriedade central dos hooks e callbacks de game thread.
3. Fazer os exemplos Lua e C++ executarem no jogo pela API documentada.
4. Integrar manifesto e handshake ao lobby, antes do início da simulação, com mensagens de conflito compreensíveis.
5. Testar dois clientes, foto automática, entrada tardia, saves e diferenças permitidas de mods locais.
6. Ampliar a API sistema por sistema e oferecer editor/empacotador sobre a mesma biblioteca de validação.

## Fontes e procedência

- [UE4SS: capacidades e necessidade de adaptação por jogo](https://github.com/UE4SS-RE/RE-UE4SS).
- [Primeiro mod Lua](https://github.com/UE4SS-RE/RE-UE4SS/blob/main/docs/guides/creating-a-lua-mod.md).
- [RegisterHook](https://docs.ue4ss.com/lua-api/global-functions/registerhook.html) e [FindFirstOf](https://docs.ue4ss.com/lua-api/global-functions/findfirstof.html).
- [Módulos C++](https://docs.ue4ss.com/guides/creating-a-c++-mod.html), base para o exemplo mínimo adaptado.
- [Declaração do desenvolvedor sobre planos de mods, janeiro de 2023](https://steamcommunity.com/app/1307890/discussions/0/3113657065282885181/). É uma declaração histórica, não prova da situação atual de um SDK. Não foi localizado um SDK oficial aplicável ao build fornecido.

REA e seus cinco submódulos continuam em `../tools/rea`; procedência em `../reports/rea-provenance.json`. Endereços do adaptador de fotos vêm de PDB/DbgHelp/dumpbin, como documentado nos relatórios. UE4SS não foi baixado, instalado ou validado nesta etapa.
