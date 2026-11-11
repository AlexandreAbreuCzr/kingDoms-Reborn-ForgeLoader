# Histórico

## 0.2.1-KR214 — 2026-11-10

- Port 0.214, seletor de mods corrigido e suporte ao módulo de rejoin fornecido.
- Perfil leve opcional e leitura das configurações aceitas pelo motor.
- Reparador de saves com validação de doador e cópia verificável.

## 0.2.0-alpha — 2026-11-10

- Loader Lua 5.4.9 e DLL x64 integrado ao jogo, com API 1 e callbacks na thread do jogo.
- Pasta Mods, instalador `.flmod`, painel Meus mods e gerador/empacotador do Dev Kit.
- Exemplos de título, limite de FPS e DLL executados no jogo local.
- Dependências, conflitos, ciclos, limites e erros Lua verificados por mod.
- Atualização do runtime v3 com backup; importador de fotos preservado.
- Negociação multiplayer, simulação compartilhada e ganho de FPS continuam sem validação/implementação conforme STATUS.md.

## 0.1.1-alpha — 2026-11-10

- Skill `forgeloader-modding` incluída no Dev Kit, com referências para manifestos/Lua e integrações C++.
- `AGENTS.md`, prompt pronto e opção Criar mod com IA no menu.
- Empacotamento preserva a pasta da skill e os recursos necessários após extrair o ZIP.
- Runtime de retratos v3 e estado do carregador geral permanecem iguais à versão anterior.

## 0.1.0-alpha — 2026-11-10

- Nome do projeto: ForgeLoader.
- Downloads separados para jogadores e desenvolvedores.
- Instalador Windows para aplicar o runtime de retratos v3 à cópia existente do jogo, com verificação, backup e restauração.
- Dev Kit com gerador, exemplos Lua/C++ e comparador offline de compatibilidade.
- Testes e documentação de instalação, desenvolvimento e limites atuais.

Na versão 0.1, carregador geral, API integrada e negociação no lobby ainda estavam pendentes.
