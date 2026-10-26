# Plan: Sugestão de cortes pelo LLM ao fim do processamento

**Issue**: 2.1.b.1
**Feature**: specs/2.1.b.1-llm-suggestion
**Data**: 2026-10-26

---

## Resumo

Cria a tabela de cortes, o cliente do OpenRouter (interface `SuggestionModel` para dublê),
a montagem da entrada (prompt do preset + frases numeradas), a validação da resposta com uma
nova tentativa e a gravação dos cortes `suggested`. O tipo de tarefa `process` chama a
sugestão ao fim; falha da sugestão fica registrada sem desfazer o processamento.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/suggestion/` — cliente, entrada, validação, orquestração.
- `packages/core/src/wordcut/` — migração e repositório de cortes, integração no `process`,
  `show_sermon` com cortes reais.

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/db/migrations/<próximo>_cuts.sql` — tabela `cuts` (entidade da spec) e colunas `suggestion_error_code`, `suggestion_error_message` em `sermons` |
| Criar | `packages/core/src/wordcut/db/cuts.py` — repositório (inserir em lote, listar por pregação, contagens por estado, apagar por pregação) |
| Criar | `packages/core/src/wordcut/suggestion/model.py` — `SuggestionModel` (protocolo `complete(system, user) -> str`) e `OpenRouterModel` (httpx, `POST https://openrouter.ai/api/v1/chat/completions`, `response_format` JSON, timeout) |
| Criar | `packages/core/src/wordcut/suggestion/request.py` — entrada: sistema = `build_prompt(preset)` + instruções do formato da resposta; usuário = frases `N: texto` |
| Criar | `packages/core/src/wordcut/suggestion/response.py` — parse e validação: `{"cuts": [{"title": str, "sentences": [int, …]}]}`; IDs existentes; sem repetição; título não vazio |
| Criar | `packages/core/src/wordcut/suggestion/__init__.py` — `suggest(conn, sermon_id, preset, model) -> SuggestionResult` (uma nova tentativa; descarte por duração; gravação) |
| Alterar | `packages/core/src/wordcut/tasks/process.py` — chama `suggest` ao fim; captura `WordcutError` e grava `suggestion_error`; resultado da tarefa inclui `suggested_cuts` |
| Alterar | `packages/core/src/wordcut/service/sermons.py` — `cuts` e `cut_counts` reais; `suggestion_error` no `show` |
| Alterar | `packages/core/pyproject.toml` — `httpx` como dependência do core |
| Criar | `packages/core/tests/test_suggestion_request.py`, `test_suggestion_response.py`, `test_suggestion.py`, `test_openrouter_model.py` (com `httpx.MockTransport`), `test_process_suggests.py` |
| Alterar | `docs/architecture/README.md` (§4; diagrama 5.1 com a sugestão), `CHANGELOG.md` |
| Alterar | `packages/core/src/wordcut/config.py` — `llm_key() -> str \| None`, chamada só pelo cliente do LLM |
| Alterar | `packages/core/src/wordcut/errors.py` e `packages/core/tests/test_errors.py` — `llm_not_configured` (saída 5) |
| Alterar | `packages/core/src/wordcut/db/sermons.py` — colunas do erro da sugestão |
| Criar | `packages/core/tests/test_cuts_repository.py` — repositório e migração 0007 |
| Alterar | `conftest.py` (raiz) — fixture autouse `no_real_llm`, que recusa `suggestion.default_model` |
| Alterar | `apps/cli/src/wordcut_cli/sermon.py` e `apps/cli/tests/test_sermon_command.py` — linha do erro da sugestão no `sermon show` legível |
| Alterar | `docs/cli.md` §5.3, §7.2, §7.4 |
| Criar | ADR da porta do LLM e do erro da sugestão gravado na pregação (complementa ADR-0010 e ADR-0014) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

Nada chama o OpenRouter de verdade: dublê de `SuggestionModel` e `httpx.MockTransport`.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Cliente HTTP | `httpx` síncrono com `MockTransport` nos testes | Simples; testável sem rede |
| Esquema da resposta | `{"cuts": [{"title": string, "sentences": [int]}]}`, frases na ordem de montagem | Mínimo que o LLM precisa devolver (§III) |
| Nova tentativa | uma, com a mesma entrada mais uma mensagem curta dizendo o erro de validação | Constituição §III: sem conserto heurístico |
| Trechos do corte | frases consecutivas viram um trecho `{from_word, to_word}`; quebra de sequência abre trecho novo | Formato de `cut segments` (docs/cli.md §8.10) |
| Faixa contínua | `range_start_word`/`range_end_word` = primeira e última palavra das frases escolhidas, na ordem da pregação | Camada contínua da 2.1.c |
| Duração estimada | soma das faixas × 0,82 (limpeza média de 18%); fora da duração permitida do preset → descartado com aviso | Regra de `sugerir-cortes.md` |
| Sem modelo ou chave | `llm_not_configured` (saída 5), registrado como `suggestion_error`, sem chamada | Item 7 deixa o modelo sem padrão |
| Erros HTTP | timeout, 4xx, 5xx → `llm_error` (saída 6), mensagem sem chave nem corpo da requisição | §VI |
| Onde guardar o erro | colunas na pregação, limpas a cada nova sugestão | `show` mostra sem consultar tarefas |
| Preset usado | o padrão; `preset_id` gravado em cada corte | 2.1.b.3 |
| Ponto de troca do LLM | fábrica `suggestion.default_model(llm_model, key)`, que os testes substituem; fixture autouse `no_real_llm` no `conftest.py` da raiz a faz falhar | Orquestrador, lacuna 1 do QA; como `processing.default_gateways` (ADR-0014) |
| Leitura da chave | `config.llm_key() -> str \| None`, chamada só pela montagem do cliente do LLM | Orquestrador, lacuna 2 |
| Código sem configuração | `llm_not_configured` (saída 5) em `errors.py`, `test_errors.py` e `docs/cli.md` §5.3 | Orquestrador, lacuna 3 |
| Reprocesso | `--force` apaga os cortes da pregação na mesma transação das palavras; teste de reprocesso | Orquestrador, lacuna 4 |
| `preset_id` do corte | `REFERENCES presets ON DELETE SET NULL`: não bloqueia `preset delete`; teste com cortes antigos | Orquestrador, lacuna 5 |
| Tarefa com sugestão falha | tarefa `succeeded`, `error_code` nulo, erro em `suggestion_error` | Orquestrador, lacuna 6; FR-005 |
| Resultado da tarefa | `show` sem `last_task`, mais `suggestion_warnings` (descartes por duração); sem `suggested_cuts`; documentado em §7.4 | Orquestrador, lacuna 7 |
| Forma no `show` | item de `cuts`: `id`, `status`, `title`, `segments`, `range_start_word`, `range_end_word`, `source`, `preset_id`, `edited`; `suggestion_error` = `{code, message}` ou `null` | Orquestrador, lacuna 8 |
| Falhas do transporte | o `OpenRouterModel` converte toda falha HTTP, de conexão e de envelope em `llm_error`; teste | Orquestrador, lacuna 9 |
| Nova tentativa | só erro de esquema ganha nova tentativa; erro HTTP é `llm_error` na hora | Orquestrador, lacuna 10; §III |
| Numeração das frases | posição 1..n; o teste usa IDs de frase diferentes da posição | Orquestrador, lacuna 11 |
| Ordem com `reorder = false` | resposta fora da ordem da pregação é inválida e conta como tentativa | Orquestrador, lacuna 12 |
| Cerca markdown | JSON dentro de cerca markdown é inválido | Orquestrador, lacuna 13; §III sem conserto |
| Documentação | §5.3, §7.2 e §7.4 atualizados no passo 6 | Orquestrador, lacuna 14 |
| CLI | `apps/cli` em escopo: uma linha com o erro da sugestão no `sermon show` legível, com teste | Orquestrador, lacuna 15 |
| Progresso | etapa `sugerindo` depois de `gravando`, documentada em §7.4; teste de etapas ajustado | Orquestrador, lacuna 16 |
| Teste do repositório | `test_cuts_repository.py` no passo 1 | Orquestrador, lacuna 17 |
| Instruções de formato | fora de `base.md` (em `suggestion/request.py`), dizendo "frases inteiras pelo número"; `base.md` não muda | Orquestrador, lacuna 18 |
| Campos da resposta | obrigatórios estritos (`title`, `sentences`); campos extras no corte (ex.: `note` de `options/reorder.md`, ou desconhecidos) aceitos e ignorados; o topo exige `cuts` | Orquestrador, Rodada 1 do QA |
| Unidade da duração | por trecho, fim da última palavra menos início da primeira (tempo da pregação), somada, ×0,82; mínimo e máximo inclusivos | Orquestrador, lacuna 19 |

---

## Ordem de implementação

- [x] **Passo 1 — Cortes no banco** — migração, repositório, `show_sermon` e `list_sermons` com
  cortes e contagens reais.
- [x] **Passo 2 — Entrada e resposta** — `request.py` e `response.py` com validação.
- [x] **Passo 3 — Modelo** — `SuggestionModel`, `OpenRouterModel` com `MockTransport`; erros.
- [x] **Passo 4 — Orquestração** — `suggest` com nova tentativa, descarte por duração,
  gravação, `llm_not_configured`.
- [x] **Passo 5 — Integração no `process`** — sugestão ao fim; erro registrado sem desfazer.
- [x] **Passo 6 — Documentação** — arquitetura, CHANGELOG, docs/cli.md §5.3.

---

## Fora de escopo

- `sermon suggest` (item 10); comandos `cut` (item 11).

---

## Verificação

- [x] Processar com dublê de LLM válido → cortes `suggested` gravados com título, trechos e
  faixa; uma chamada.
- [x] Primeira resposta inválida e segunda válida → cortes gravados; duas chamadas.
- [x] Duas inválidas → nenhum corte; pregação `processed`; `suggestion_error` = `llm_error`.
- [x] Sem modelo ou chave → `processed` sem cortes; `suggestion_error` = `llm_not_configured`.
- [x] Frase inexistente na resposta → inválida (conta tentativa).
- [x] Corte fora da duração permitida → descartado com aviso; os outros gravados.
- [x] A chave não aparece em erro, log nem resultado.
- [x] `sermon show` traz `cuts` e `cut_counts` reais.
- [x] Quality gates limpos.
