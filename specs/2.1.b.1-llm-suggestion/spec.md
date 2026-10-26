# Spec: Sugestão de cortes pelo LLM ao fim do processamento

**Issue**: 2.1.b.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/2.1.b-llm-script-suggestion.md §2.1.b.1, §2.1.b.3;
docs/cli.md §7.4; constituição §I, §III; ADR-0010
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

Ao fim do processamento, o sistema pede ao LLM, uma única vez, os cortes sugeridos da
pregação, segundo o preset padrão. Só a pregação vai ao LLM, como frases numeradas sem
tempo; a resposta segue um esquema JSON validado, com uma nova tentativa. Os cortes válidos
ficam gravados como `suggested`, prontos para a equipe escolher.

---

## Cenários de aceite

**Cenário: sugestão automática**
- **Dado** uma pregação processada, o modelo e a chave configurados e o preset padrão
- **Quando** o processamento termina
- **Então** o LLM é chamado uma vez com as frases numeradas e o prompt do preset, e os cortes
  válidos ficam gravados como `suggested`, cada um com título, frases em ordem e faixa
  contínua na pregação

**Cenário: resposta inválida, nova tentativa**
- **Dado** um LLM que responde JSON fora do esquema na primeira vez e válido na segunda
- **Quando** a sugestão roda
- **Então** os cortes da segunda resposta são gravados, com duas chamadas no total

**Cenário: duas respostas inválidas**
- **Dado** um LLM que responde fora do esquema duas vezes
- **Quando** a sugestão roda
- **Então** nenhum corte é gravado, a pregação continua `processed` e o erro `llm_error` fica
  registrado na tarefa, visível no `sermon show` (`suggestion_error`)

**Cenário: sem configuração do LLM**
- **Dado** modelo ou chave não configurados
- **Quando** o processamento termina
- **Então** a pregação fica `processed` sem cortes e com `suggestion_error` dizendo o que falta

### Casos de borda

- Frase citada que não existe na pregação → resposta inválida (conta como tentativa).
- Corte cuja duração estimada fica fora da duração permitida do preset → descartado com
  aviso no resultado; os outros ficam.
- Nenhum corte válido numa resposta válida → `processed` sem cortes, sem erro.
- A chave do LLM nunca aparece em log, erro ou resultado.
- Testes nunca chamam o OpenRouter de verdade.

---

## Requisitos funcionais

- **FR-001**: Ao fim do `process`, a sugestão DEVE rodar uma vez com o preset padrão.
- **FR-002**: A entrada ao LLM DEVE ser o prompt do preset (item 8) mais as frases numeradas
  da pregação, sem tempos.
- **FR-003**: A resposta DEVE ser validada contra um esquema JSON (lista de cortes com título
  e IDs de frase em ordem); inválida → uma nova tentativa; inválida de novo → `llm_error`.
- **FR-004**: Cada corte válido DEVE ser gravado como `suggested`, com título, trechos
  (faixas de palavras) e faixa contínua (primeira e última frase).
- **FR-005**: Falha da sugestão NÃO DEVE desfazer o processamento.
- **FR-006**: A chamada DEVE ir ao OpenRouter com o modelo e a chave configurados (item 7).

---

## Entidades e dados

- **Corte (`cut`)**: id, sermon_id, status (`suggested` | `chosen` | `discarded`), title,
  segments (JSON `[{from_word, to_word}]` em ordem), range_start_word, range_end_word,
  source (`llm` | `admin`), preset_id, edited, caption (JSON), render_options (JSON),
  created_at, updated_at.
- **Pregação**: ganha `suggestion_error` (código e mensagem) ou equivalente na última tarefa.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — cliente do OpenRouter, montagem da entrada, validação,
  migração e repositório de cortes, integração ao fim do `process`.
- Testes com um LLM dublê.

### Fora de escopo
- `sermon suggest` (item 10) e comandos de `cut` (item 11).

### Integrações externas
- OpenRouter (dublê nos testes).

---

## Pressupostos

- O cliente HTTP é `httpx` (já usado nos testes da API).
- A duração estimada de um corte é a soma das faixas de palavras, descontando a limpeza
  média de 15–20% (regra de `sugerir-cortes.md`), só para o descarte por duração.
