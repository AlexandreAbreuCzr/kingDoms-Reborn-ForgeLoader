# Criar um mod com ajuda de IA

## Começar

1. Extraia o **ForgeLoader Dev Kit** e abra a pasta em um assistente de programação que consiga ler e editar seus arquivos.
2. No Codex, use a skill **forgeloader-modding**. Ela acompanha o projeto em `.agents/skills/forgeloader-modding/`.
3. Descreva sua ideia usando o pedido abaixo. Para outra IA, forneça `AGENTS.md`, a pasta completa da skill e os arquivos de código necessários.

```text
Use $forgeloader-modding para trabalhar neste ForgeLoader Dev Kit.
Leia AGENTS.md e confira o estado atual das APIs antes de implementar.

Meu mod: [descreva o que ele deve fazer].
No multiplayer: [só muda minha tela / muda as regras da partida / ainda não sei].

Crie ou edite o projeto, explique quais partes conseguem executar hoje,
valide o manifesto e mostre como testar. Se faltar uma integração com o
jogo, identifique a função necessária e marque essa parte como pendente.
```

Você também encontra este texto na opção **4 — Criar mod com IA** de `Abrir-DevKit.cmd`.

## O que a skill orienta

- Escolher entre script Lua, módulo C++ e trabalho no adaptador do jogo.
- Usar a estrutura real dos exemplos e do manifesto.
- Conferir versões, dependências, arquivos e impacto multiplayer.
- Preservar o limite entre validação fora do jogo e comportamento comprovado no jogo.
- Mapear integrações nativas por evidência, em vez de inventar funções ou endereços.

O kit fornece instruções para sua IA; não inclui um modelo de IA embutido nem pede chave de API. Cada assistente precisa receber acesso aos arquivos pelo ambiente que você escolher. Não é garantido que toda IA reconheça automaticamente `AGENTS.md` ou skills; nesses casos, peça explicitamente a leitura desses arquivos.

## Limite importante deste alpha

O runtime 0.2 executa mods Lua e DLL locais. Use docs/MOD-API.md e os exemplos em modkit/examples/forgeloader. A negociação no lobby, simulação compartilhada e acesso Lua genérico aos objetos Unreal continuam em desenvolvimento. Uma integração nova precisa de implementação e teste; não basta escrever chamadas com nomes inventados. Peça à IA um pacote .flmod para instalar pelo loader.

Formato de skills e descoberta no Codex: [documentação oficial](https://learn.chatgpt.com/docs/build-skills). Instruções de projeto: [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
