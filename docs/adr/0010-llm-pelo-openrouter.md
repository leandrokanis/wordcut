# ADR-0010: LLM pelo OpenRouter com critérios no código

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

As sugestões de cortes usam um LLM uma vez por pregação (princípio III). Os critérios
teológicos não podem ser editados pela interface (princípio I).

## Decisão

As chamadas vão ao OpenRouter, com modelo e chave configuráveis. O prompt é montado com
textos fixos no pacote `core` (prompt base e um trecho por critério e nível), mais os
números e as instruções adicionais do preset. A resposta segue um esquema JSON validado,
com uma nova tentativa.

## Consequências

- Trocar de modelo é configuração, não código.
- Mudar um critério exige commit revisado.
