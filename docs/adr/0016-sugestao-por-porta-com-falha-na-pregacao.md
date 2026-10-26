# ADR-0016: Sugestão de cortes por porta, com a falha gravada na pregação

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0010](0010-llm-pelo-openrouter.md), que continua valendo (OpenRouter,
critérios no código, esquema validado com uma nova tentativa), e a
[ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md), cujo padrão de porta
substituível repete (item 2.1.b.1, [docs/cli.md](../cli.md) §7.4).

## Contexto

O processamento termina pedindo os cortes ao LLM uma vez (constituição §III). O LLM é um
serviço externo pago, com chave: os testes não podem chamá-lo, e a chave não pode aparecer em
erro, log ou resultado (§VI). O processo destacado da tarefa só recebe o ID da tarefa, então o
dublê não chega por argumento.

A sugestão pode falhar por motivos que nada têm a ver com o processamento: modelo ou chave
não configurados, OpenRouter fora do ar, resposta fora do esquema duas vezes. Marcar a
pregação `failed` jogaria fora a transcrição e o vídeo, que custam GPU e tempo, por uma
falha que se resolve pedindo a sugestão de novo.

## Decisão

- O LLM fica atrás da porta `wordcut.suggestion.SuggestionModel`
  (`complete(system, user) -> str`). `suggestion.default_model(llm_model, key)` monta a
  implementação real (`OpenRouterModel`, `httpx` síncrono); a sugestão a chama no processo
  que roda a tarefa. Os testes substituem `default_model`, e uma fixture da suíte
  (`no_real_llm`) faz a real falhar se for alcançada.
- A sugestão confere o modelo (configurações) e a chave (`config.llm_key()`, a única leitura
  em claro) antes de montar o modelo; faltando algum, `llm_not_configured` (saída 5), sem
  chamada.
- O `OpenRouterModel` converte toda falha do transporte (timeout, conexão, HTTP 4xx/5xx,
  envelope sem a resposta) em `llm_error`, sem a chave, as mensagens nem o corpo da
  resposta. Só a resposta fora do esquema ganha a nova tentativa; erro de transporte é
  `llm_error` na hora.
- O resultado da última sugestão fica na pregação: `suggestion_error_code` e
  `suggestion_error_message` (migração 0007), limpos quando uma sugestão dá certo. No
  `process`, a falha da sugestão não desfaz nada: a tarefa termina `succeeded`, a pregação
  `processed`, e `sermon show` traz `suggestion_error`.

## Consequências

- A sugestão é testada de ponta a ponta, dentro do `process`, com dublê ou com
  `httpx.MockTransport`; nenhum teste fala com o OpenRouter.
- Uma pregação processada pode ficar sem cortes e com `suggestion_error`; quem lê a tarefa
  vê `succeeded` e precisa olhar a pregação para saber da sugestão. Refazer só a sugestão é
  `sermon suggest` (item 2.1.b.2).
- O `httpx` passa a ser dependência do `core`.
