# QA — 2.1.b.1 — Sugestão de cortes pelo LLM ao fim do processamento

## Plano de QA — 2026-10-26

**baseline_commit**: 2956c4c758f3a2dffc0209f07cdc41aeb40546f9
**Componentes em escopo**: `packages/core` (novo `wordcut.suggestion` com `model.py`,
`request.py`, `response.py` e `__init__.py`; migração `0007_cuts.sql` e `db/cuts.py`;
`tasks/process.py`; `service/sermons.py`; `errors.py` com `llm_not_configured`; `config.py`
com o leitor da chave em claro; `pyproject.toml` com `httpx` e `uv.lock`); `conftest.py` da
raiz (guarda autouse contra o LLM real); `apps/cli` (`wordcut_cli/sermon.py`, só a linha do
erro da sugestão no `sermon show` legível — decisão do QA, lacuna "sermon show legível"); documentação
(`docs/cli.md` §5.3, §7.2, §7.4; `docs/architecture/README.md` §4 e diagrama 5.1;
`CHANGELOG.md`).
**Suítes que valem como prova**:
- Python, por arquivo:
  `uv run pytest packages/core/tests/test_suggestion_request.py packages/core/tests/test_suggestion_response.py packages/core/tests/test_openrouter_model.py packages/core/tests/test_suggestion.py packages/core/tests/test_process_suggests.py packages/core/tests/test_cuts_repository.py -q`
- Python, suíte completa: `uv run pytest -q` (inclui `test_db.py`, `test_errors.py`,
  `test_sermons_service.py`, `test_process_task.py` e `apps/cli/tests/test_sermon_command.py`,
  que mudam com este item)
- Checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`
- Lock: `uv lock --check` (o `httpx` passa a ser dependência do core)

**Regras da barra** (decisões que o plano não tomou, fixadas pelo QA na opção mais
conservadora; detalhes nas linhas `⚠️ LACUNA` de `tdd.md`)
- **Nenhum teste chama o OpenRouter.** Existe fixture autouse no `conftest.py` da raiz,
  análoga a `no_real_processing`, que faz falhar a construção do modelo real; o
  `OpenRouterModel` só é exercitado com `httpx.MockTransport`. O QA confere com
  `grep -rn "openrouter.ai" packages/*/tests apps/*/tests` (só asserções de URL no transport).
- **Chave sentinela.** Os testes gravam uma chave fictícia e distinta no config temporário e
  a procuram em `str(error)`, `error.to_dict()` (inclusive `details`), na linha de `tasks`
  (`error_message`, `error_details`, `result`), no `show_sermon`, no `caplog` em `DEBUG` e no
  stdout/stderr da CLI. Prova positiva: o header `Authorization: Bearer <chave>` chega ao
  transport (FR-006).
- **Mensagem de erro HTTP** não traz chave, corpo da requisição (prompt, frases) nem corpo
  da resposta: o transport responde 401 com um corpo que ecoa a chave e o prompt.
- **Sugestão falha ≠ tarefa falha.** Com `llm_error` ou `llm_not_configured`, a tarefa
  `process` termina `succeeded` com `error_code` nulo, a pregação fica `processed` com
  palavras e frases, e o erro fica em `suggestion_error` no `show` e no resultado da tarefa.
- **Toda falha do transporte vira `llm_error`.** `httpx.HTTPError` (timeout, conexão, 4xx,
  5xx) e envelope malformado (200 não JSON, sem `choices`, `content` nulo) viram
  `WordcutError("llm_error")` dentro do `OpenRouterModel`; nada disso pode cair no
  `except BaseException` de `process._run` e marcar a pregação `failed`.
- **Nova tentativa só para erro de esquema.** Erro HTTP → `llm_error` na hora, sem segunda
  chamada (§III: uma chamada por pregação).
- **Esquema estrito, sem conserto (§III).** Inválidos: texto que não é JSON, JSON dentro de
  cerca markdown, raiz que não é objeto, `cuts` ausente ou não lista, `title` ausente, vazio,
  só espaços ou não string, `sentences` ausente, vazia ou não lista, ID não inteiro (`true`,
  `3.0`, `"3"`), ID inexistente, ID repetido no mesmo corte e, com `reorder = false`, frases
  fora da ordem da pregação. `{"cuts": []}` é válido.
- **Numeração das frases** pode ser ID ou posição, mas o teste usa uma pregação cujos IDs de
  frase não coincidem com a posição (segunda pregação no mesmo banco ou reprocesso) e confere
  as palavras de cada trecho.
- **Duração estimada** = Σ por trecho (fim da última palavra − início da primeira, em tempo
  da pregação) × 0,82; fora de `[allowed.min, allowed.max]` (inclusivo) → descartado com
  aviso, os outros gravados.
- **Resultado da tarefa** = `sermon show` sem `last_task` (§7.4), com `cuts`, `cut_counts` e
  `suggestion_error` reais; os avisos de descarte vão em `suggestion_warnings`, documentado
  em §7.4. `suggested_cuts` só vale se documentado em §7.4.
- **Forma no `show`**: cada item de `cuts` traz `id`, `status`, `title`, `segments`
  (`[{from_word, to_word}]`), `range_start_word`, `range_end_word`, `source`, `preset_id`,
  `edited`; `suggestion_error` é `{"code", "message"}` ou `null`.
- **Reprocesso (`--force`)** apaga os cortes da pregação na mesma transação das palavras,
  sem `IntegrityError`; `preset_id` não impede `preset delete` de um preset não padrão.
- **Comentários e textos**: identificadores e comentários em inglês, tipos de CONTRIBUTING §5;
  mensagens ao usuário em português; nenhum nome de pessoa nem segredo; `base.md` e os
  textos dos critérios intocados (constituição §I).
- Mutações cobradas na avaliação: as linhas `🧬 EXIGE` de `tdd.md`. Mutação manual desfeita na
  hora.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Cortes no banco | (a) banco novo em `user_version` 7 com a tabela `cuts` (colunas da entidade da spec; `CHECK` de `status` em `suggested`/`chosen`/`discarded` e de `source` em `llm`/`admin`) e as colunas `suggestion_error_code`/`suggestion_error_message` em `sermons`; banco na versão 6 migra sem perder `presets`, `sermons`, `words`; migração sem `BEGIN`/`COMMIT`; (b) repositório grava em lote e relê todos os campos (`segments` JSON em ordem, faixas, `source`, `preset_id`, `edited` falso, `caption`/`render_options`, datas), lista por pregação em ordem estável, conta por estado e apaga por pregação; (c) apagar a pregação apaga os cortes em cascata; `preset_id` não bloqueia apagar um preset não padrão; (d) `show_sermon` devolve `cuts` reais na forma da barra e `suggestion_error`; `list_sermons`/`show_sermon` devolvem `cut_counts` reais com cortes nos três estados; (e) testes antigos (`test_sermons_service.py`, `test_sermon_command.py`) mudam só em `cuts`/`cut_counts`/`suggestion_error` | `test_cuts_repository.py` (novo; lacuna "teste do repositório") e `test_db.py` com SQLite real em `tmp_path`; `test_sermons_service.py` pela interface do serviço, cortes inseridos pelo repositório; leitura do `.sql` |
| 2 — Entrada e resposta | **Entrada**: (a) a mensagem de sistema contém `build_prompt(preset)` (comparada com a função, não com string copiada) e as instruções de formato com o esquema `{"cuts": [{"title", "sentences"}]}`, dizendo que a unidade é a frase inteira; (b) a do usuário tem uma linha `N: texto` por frase da pregação, todas, em ordem, e nenhum `start`/`end` nem tempo formatado; (c) pura, sem rede. **Resposta**: (d) válidas: `{"cuts": []}`, um corte, vários cortes, mesma frase em cortes distintos, `reorder = true` com ordem trocada; (e) cada inválido da regra "esquema estrito" gera erro de validação com motivo legível, um teste por caso (parametrizado) | `test_suggestion_request.py` e `test_suggestion_response.py`, unidade pela interface pública de `request.py`/`response.py`, preset de `default_preset()` e frases de uma pregação em banco temporário |
| 3 — Modelo | (a) `OpenRouterModel.complete(system, user)` faz `POST https://openrouter.ai/api/v1/chat/completions` com `Authorization: Bearer <chave>`, `model` das configurações, mensagens de sistema e de usuário, `response_format` JSON e timeout em constante nomeada, e devolve `choices[0].message.content`; (b) 401, 429, 500, `httpx.TimeoutException`, `httpx.ConnectError`, 200 não JSON, 200 sem `choices` e `content` nulo → `WordcutError("llm_error")` (saída 6), sem chave, prompt, frases nem corpo da resposta na mensagem e em `details`; (c) cliente ou transport injetável; guarda autouse ativa; (d) `SuggestionModel` é `Protocol` e o dublê do teste passa no `mypy --strict`; (e) `httpx` nas dependências do core e `uv lock --check` limpo | `test_openrouter_model.py` com `httpx.MockTransport` que registra a requisição; chave sentinela; `uv run mypy` |
| 4 — Orquestração | (a) resposta válida → uma chamada; cortes `suggested`, `source = llm`, `preset_id` do preset, `edited` falso, título; frases consecutivas viram um trecho e a quebra abre outro (`[3, 4, 5, 9, 10]` → dois trechos com `from_word`/`to_word` das frases 3–5 e 9–10); faixa = primeira e última palavra na ordem da pregação (`[9, 10, 3]` com `reorder = true` → trechos 9–10 e 3, faixa de 3 a 10); (b) inválida e depois válida → duas chamadas; a segunda leva a mesma entrada mais o motivo da invalidação; grava os da segunda; (c) duas inválidas → exatamente duas chamadas, `llm_error`, nenhum corte gravado; (d) frase inexistente conta como tentativa; (e) duração: bruto acima do máximo e estimado dentro → fica; estimado acima do máximo ou abaixo do mínimo → descartado com aviso; os outros gravados; estimado igual a `min` e a `max` → fica; (f) resposta válida sem cortes, ou com todos descartados → nada gravado, sem erro; (g) sem `llm_model`, sem chave ou sem os dois → `llm_not_configured` (saída 5), dublê com zero chamadas, mensagem diz o que falta e não traz a chave; (h) sugestão seguinte limpa o `suggestion_error` anterior; (i) `llm_error` de transporte → sem segunda chamada | `test_suggestion.py` com dublê de `SuggestionModel` que roteiriza respostas e guarda as entradas; banco real com palavras e frases via `transcripts.replace`; `test_errors.py` com `llm_not_configured: 5` |
| 5 — Integração no `process` | (a) `FakeGateways` + dublê de LLM pelo ponto de troca do `process`, modelo e chave configurados: pregação `processed`, cortes `suggested` gravados, uma chamada com o prompt do preset padrão, resultado da tarefa = `show` sem `last_task` com os cortes; (b) duas inválidas → tarefa `succeeded`, pregação `processed` com palavras e frases, zero cortes, `suggestion_error.code = llm_error` no `show_sermon` e no resultado; (c) sem configuração → `processed`, zero cortes, `llm_not_configured`, dublê sem chamada; (d) `OpenRouterModel` real com `MockTransport` que levanta `httpx.ConnectError` → pregação `processed`, não `failed`; (e) `--force` numa pregação com cortes → antigos removidos, novos gravados, sem `IntegrityError`; (f) chave sentinela ausente do resultado, da linha `tasks`, do `show` e do `caplog`; (g) `sermon show --json` pela CLI traz `cuts`, `cut_counts` e `suggestion_error`; o legível mostra o erro da sugestão; (h) `test_process_task.py` continua verde sem rede (sem configuração cai em `llm_not_configured`); etapas de progresso batem com §7.4 | `test_process_suggests.py` com `tasks.execution.start(..., detach=False)` como `test_process_task.py`; `apps/cli/tests/test_sermon_command.py` por `main(argv)` + `capsys` |
| 6 — Documentação | `docs/cli.md` §5.3 com `llm_not_configured` (saída 5); §7.4 sem "chega no item 9", descrevendo a sugestão ao fim, `suggestion_error` sem desfazer o processamento, `suggestion_warnings` e a etapa nova, se houver; §7.2 com `suggestion_error` e a forma dos cortes; `docs/architecture/README.md` §4 (tabela `cuts`, migração 0007, `wordcut.suggestion`) e diagrama 5.1 com o OpenRouter; `CHANGELOG.md` em "Não lançado"; nenhum nome de pessoa nem segredo | `git diff 2956c4c -- docs/ CHANGELOG.md`; leitura; sem teste automatizado |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "sugestão automática" / Verificação 1 — uma chamada com frases numeradas e prompt do preset; cortes `suggested` com título, frases em ordem e faixa contínua | Passo 5 (a); Passo 4 (a); Passo 2 (a)(b) |
| Cenário "resposta inválida, nova tentativa" / Verificação 2 — duas chamadas, cortes da segunda | Passo 4 (b); mutações "sem nova tentativa" e "três chamadas" |
| Cenário "duas respostas inválidas" / Verificação 3 — nenhum corte, `processed`, `llm_error` em `suggestion_error` | Passo 4 (c); Passo 5 (b)(g) |
| Cenário "sem configuração do LLM" / Verificação 4 — `processed` sem cortes, `suggestion_error` = `llm_not_configured` dizendo o que falta | Passo 4 (g); Passo 5 (c); `test_errors.py` |
| Borda — frase citada inexistente → inválida, conta tentativa / Verificação 5 | Passo 2 (e); Passo 4 (d) |
| Borda — fora da duração permitida → descartado com aviso, os outros ficam / Verificação 6 | Passo 4 (e); `suggestion_warnings` no resultado (Passo 5 a) |
| Borda — resposta válida sem cortes válidos → `processed` sem cortes, sem erro | Passo 4 (f) |
| Borda — chave nunca em log, erro ou resultado / Verificação 7 | Passo 3 (b); Passo 4 (g); Passo 5 (f); regra da chave sentinela |
| Borda — testes nunca chamam o OpenRouter | Guarda autouse; Passo 3 (c); grep da regra da barra |
| Verificação 8 — `sermon show` traz `cuts` e `cut_counts` reais | Passo 1 (d); Passo 5 (g) |
| FR-001 — sugestão uma vez ao fim do `process`, com o preset padrão | Passo 5 (a): uma chamada, `preset_id` = padrão |
| FR-002 — prompt do preset + frases numeradas, sem tempos | Passo 2 (a)(b); mutação "tempos nas linhas" |
| FR-003 — esquema validado, uma nova tentativa, depois `llm_error` | Passo 2 (d)(e); Passo 4 (b)(c)(i) |
| FR-004 — corte `suggested` com título, trechos e faixa contínua | Passo 4 (a); Passo 1 (b) |
| FR-005 — falha da sugestão não desfaz o processamento | Passo 5 (b)(c)(d) |
| FR-006 — OpenRouter com o modelo e a chave configurados | Passo 3 (a): URL, `model`, header Bearer |
| 2.1.b.3 — saber com qual preset cada sugestão foi gerada | Passo 4 (a) e Passo 1 (d): `preset_id` gravado e mostrado |
| Constituição §I — o conteúdo do corte vem do LLM; o código não acrescenta nem tira frases | Passo 4 (a)(e): frases gravadas = frases da resposta; o descarte é do corte inteiro |
| Constituição §III — uma chamada; só a pregação; formato enxuto; esquema sem conserto | Passo 2 (b)(e); Passo 4 (b)(c)(i); frases só da tabela `sentences` |
| Constituição §VI / ADR-0010 — segredo fora de erro e log; prompt de textos fixos do core | Regra da chave sentinela; Passo 2 (a) com `build_prompt` |
| Verificação 9 — quality gates limpos | `uv run pytest -q`; `uv run ruff check . && uv run ruff format --check . && uv run mypy`; `uv lock --check` |

## Rodada 1 — 2026-10-26 — working tree sobre 2956c4c

**baseline_commit**: 2956c4c758f3a2dffc0209f07cdc41aeb40546f9
**Componentes avaliados**: `packages/core` (`wordcut.suggestion`, `db/cuts.py`, migração 0007,
`tasks/process.py`, `service/sermons.py`, `db/sermons.py`, `config.py`, `errors.py`,
`pyproject.toml`/`uv.lock`); `conftest.py` da raiz; `apps/cli` (`sermon show`); documentação
(`docs/cli.md`, `docs/architecture/README.md`, `CHANGELOG.md`, `README.md`, ADR-0016)
**Suítes**: Python `uv run pytest -q` ✅ (822 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ ·
`mypy` ✅ (73 arquivos) · `mypy --strict` nos 6 testes novos ✅ · `uv lock --check` ✅

**Fatos relatados pelo implementador, julgados contra a barra**
- `suggest(connection, sermon_id, preset)`, com o modelo vindo de `suggestion.default_model`:
  segue a decisão 1 (fábrica substituível + `no_real_llm`), que substitui o
  `suggest(conn, sermon_id, preset, model)` do Contexto de código. Conforme.
- Campos extras por corte (ex.: `note` de `options/reorder.md`) aceitos; campos obrigatórios
  estritos; topo exige `cuts`: o código segue a decisão do orquestrador (sondado:
  `{"cuts": [{"title", "sentences", "note"}]}` é válido). Falta o teste; ver Passo 2.

**Chave e rede**: nenhum teste chama o OpenRouter (`grep "openrouter.ai"` nos testes vazio;
`OpenRouterModel` só com `httpx.MockTransport`; `no_real_llm` recusa a fábrica real). A chave em
claro só é lida por `config.llm_key()` em `_configured_model`; erros de transporte saem com
`from None` e mensagem fixa; `details` só com `status`/`missing`/`reason`. Nenhum caminho de
vazamento encontrado.

**Mutações** (cópia em scratchpad, 34 aplicadas e desfeitas, cópia conferida igual à worktree):
31 mortas. Sobreviveram: "frase repetida aceita" (EXIGE vermelha), "nova tentativa sem o
motivo", "campo extra no corte recusado" e "título sem strip" (fora da barra).

**Comentários**: os novos são de intenção, restrição externa com fonte, referência, formato
ou contrato (CONTRIBUTING §5), em inglês; mensagens ao usuário em português; nenhum nome de
pessoa nem segredo. **ADR-0016**: formato Nygard, complementa ADR-0010/0014, indexada em
`docs/adr/README.md`, coerente com o código.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cortes no banco | PASS | `test_cuts_repository.py` (8; cascata, SET NULL, CHECKs, 6→7 sem `BEGIN`/`COMMIT`), `test_sermons_service.py` (cortes, contagens 1/2/1, `suggestion_error`); mutações "cut_counts zero" e "cuts vazio" mortas |
| 2 — Entrada e resposta | PARCIAL | Entrada (a)(b) e os 20 inválidos provados; mas a mutação EXIGE "frase repetida no corte aceita" sobrevive: `cut_with(sentences=[3, 4, 3])` em `test_suggestion_response.py:140` roda com `reorder=False` e cai na checagem de ordem (`response.py:67`), então nada prova `response.py:65`. Campos extras aceitos (decisão do orquestrador) sem teste: a mutação que os recusa sobrevive |
| 3 — Modelo | PASS | `test_openrouter_model.py`: URL, Bearer, `model`, mensagens, `response_format`, `TIMEOUT_SECONDS`; 401/429/500/timeout/conexão/não JSON/sem `choices`/`choices` vazia/`content` nulo → `llm_error` (6) sem chave, prompt, frases nem corpo, inclusive no `caplog` DEBUG; `httpx` no core, lock limpo |
| 4 — Orquestração | PARCIAL | (a)(c)–(i) provados, mutações mortas; (b) "a segunda leva a mesma entrada mais o motivo" não é provado: `test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason` (`test_suggestion.py:221`) procura "JSON", que o próprio `RETRY_NOTE` já contém; a mutação `RETRY_NOTE.format(reason='')` sobrevive |
| 5 — Integração no `process` | PASS | `test_process_suggests.py` (6): cortes com o preset padrão e resultado = `show` sem `last_task` + `suggestion_warnings`; duas inválidas e sem configuração → `succeeded`/`processed`; `ConnectError` real → `processed`; `--force` troca os cortes; chave ausente de `tasks`, `show` e log; `test_sermon_command.py` legível e `--json`; etapa `sugerindo` em `test_process_task.py` |
| 6 — Documentação | PASS | `docs/cli.md` §5.3, §7.2, §7.4; `docs/architecture/README.md` §4 e 5.1; `CHANGELOG.md` em "Não lançado"; ADR-0016 e índice; `base.md` e textos dos critérios intocados |

### Critérios de aceite
- ✅ Sugestão automática / Verificação 1 — `test_processing_ends_by_saving_the_cuts_the_llm_suggests_with_the_default_preset`, `test_a_valid_answer_is_saved_as_suggested_cuts_with_one_segment_per_run_of_sentences`
- ✅ Resposta inválida, nova tentativa / Verificação 2 — `test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason` (duas chamadas, cortes da segunda; o motivo na segunda não é provado, Passo 4)
- ✅ Duas respostas inválidas / Verificação 3 — `test_two_answers_outside_the_schema_are_an_llm_error_kept_on_the_sermon_without_cuts`, `test_a_failed_suggestion_leaves_the_task_succeeded_and_the_sermon_processed`
- ✅ Sem configuração do LLM / Verificação 4 — `test_without_the_model_or_the_key_the_llm_is_not_called_and_the_error_says_what_is_missing[3]`, `test_without_the_llm_configured_the_sermon_is_processed_without_cuts_nor_a_call`
- ✅ Frase inexistente conta tentativa / Verificação 5 — `test_a_cited_sentence_that_does_not_exist_costs_an_attempt`
- ✅ Fora da duração → descartado com aviso / Verificação 6 — `test_cuts_whose_estimated_duration_falls_outside_the_allowed_one_are_dropped_with_a_warning`
- ✅ Resposta válida sem cortes válidos — `test_a_valid_answer_without_cuts_to_keep_saves_nothing_and_is_no_error[2]`
- ✅ Chave nunca em log, erro ou resultado / Verificação 7 — `test_any_failure_to_get_an_answer_is_an_llm_error_without_key_messages_or_body[9]`, `test_the_llm_key_reaches_only_the_request_never_the_task_the_sermon_or_the_log`
- ✅ Testes nunca chamam o OpenRouter — `no_real_llm` + `test_the_real_model_is_refused_inside_the_test_suite`; grep vazio
- ✅ Verificação 8 — `test_listed_and_shown_sermons_count_their_cuts_by_state`, `test_show_tells_why_the_last_suggestion_failed`
- ✅ FR-001 — uma chamada, `preset_id` do padrão (`test_process_suggests.py`)
- ✅ FR-002 — `test_the_user_message_numbers_every_sentence_from_1_in_order_without_times`, `test_the_system_message_is_the_preset_prompt_then_the_answer_schema_by_whole_sentences`
- ✅ FR-003 — `test_suggestion_response.py` + nova tentativa e `llm_error` em `test_suggestion.py`
- ✅ FR-004 — trechos, faixa e `suggested` em `test_suggestion.py`; repositório em `test_cuts_repository.py`
- ✅ FR-005 — `test_a_failed_suggestion_leaves_the_task_succeeded_and_the_sermon_processed`, `test_openrouter_out_of_reach_leaves_the_sermon_processed_not_failed`
- ✅ FR-006 — `test_completing_posts_the_messages_to_openrouter_with_the_key_and_returns_the_content`, `test_the_model_is_built_with_the_configured_model_and_key`
- ✅ 2.1.b.3 — `preset_id` gravado e mostrado; `test_deleting_the_preset_of_old_cuts_keeps_them_without_their_preset`
- ✅ Constituição §I — frases gravadas = frases da resposta; descarte do corte inteiro
- ✅ Constituição §III — uma chamada + uma nova tentativa só por esquema; cerca markdown inválida; sem tempos
- ✅ Constituição §VI / ADR-0010 — chave sentinela; prompt por `build_prompt`
- ✅ Verificação 9 — pytest, ruff, mypy e `uv lock --check` verdes

### Veredito geral: PARCIAL
Sem FAIL e suítes verdes; reabrir 2 (teste de frase repetida com `reorder=true` e teste de campo
extra aceito) e 4 (teste que prove o motivo da invalidação na segunda mensagem).

## Rodada 2 — 2026-10-26 — working tree sobre 2956c4c

**baseline_commit**: 2956c4c758f3a2dffc0209f07cdc41aeb40546f9
**Componentes avaliados**: `packages/core` (`wordcut.suggestion`: `response.py`, `__init__.py`;
`tests/test_suggestion_response.py`, `tests/test_suggestion.py`); demais componentes da Rodada 1
só pela suíte completa
**Suítes**: Python `uv run pytest -q` ✅ (825 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ ·
`mypy` ✅ (73 arquivos) · `mypy --strict` nos 2 testes alterados ✅ · `uv lock --check` ✅

**Mudanças desde a Rodada 1**: só testes. `response.py` e `suggestion/__init__.py` são iguais
byte a byte à cópia da Rodada 1. O `plan.md` ganhou a decisão "Campos da resposta"
(orquestrador, Rodada 1). Nenhum teste chama o OpenRouter (`grep "openrouter.ai"` nos testes vazio).

**Mutações** (cópia em scratchpad, 11 aplicadas e desfeitas, cópia conferida igual à worktree):
10 mortas. Mortas: "frase repetida aceita" (EXIGE), "campo extra no corte recusado", "só o
`note` recusado", "topo sem exigir `cuts`", `RETRY_NOTE.format(reason='')`, motivo genérico,
nome do tipo da exceção como motivo, segunda mensagem sem a entrada original, motivo antes da
entrada, sem nova tentativa. Sobreviveu: "título sem strip" (fora da barra, como na Rodada 1).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Cortes no banco | PASS | Sem mudança desde a Rodada 1; `test_cuts_repository.py` e `test_sermons_service.py` verdes |
| 2 — Entrada e resposta | PASS | `test_a_sentence_repeated_in_a_cut_is_invalid_even_when_reordering_is_allowed` (`test_suggestion_response.py:115`) roda com `reorder=True` e mata a mutação EXIGE (remover `response.py:65-66`); `test_an_answer_in_the_schema_gives_its_cuts[note of the reorder option ignored]` e `[unknown field in the cut ignored]` provam campos extras aceitos e ignorados; `[cuts missing]` prova o topo exigindo `cuts` |
| 3 — Modelo | PASS | Sem mudança desde a Rodada 1; `test_openrouter_model.py` verde |
| 4 — Orquestração | PASS | (b) `test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason` (`test_suggestion.py:210`) compara a mensagem de sistema, exige a entrada original como prefixo e o texto exato que `parse_response` dá à recusa no acréscimo; `reason=''`, motivo genérico e nome do tipo ficam vermelhos. (a)(c)–(i) como na Rodada 1 |
| 5 — Integração no `process` | PASS | Sem mudança desde a Rodada 1; `test_process_suggests.py` e `test_sermon_command.py` verdes |
| 6 — Documentação | PASS | Sem mudança desde a Rodada 1 |

### Critérios de aceite
- ✅ Sugestão automática / Verificação 1 — como na Rodada 1
- ✅ Resposta inválida, nova tentativa / Verificação 2 — `test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason` (duas chamadas, cortes da segunda e agora o motivo específico na segunda mensagem)
- ✅ Duas respostas inválidas / Verificação 3 — como na Rodada 1
- ✅ Sem configuração do LLM / Verificação 4 — como na Rodada 1
- ✅ Frase inexistente conta tentativa / Verificação 5 — como na Rodada 1
- ✅ Fora da duração → descartado com aviso / Verificação 6 — como na Rodada 1
- ✅ Resposta válida sem cortes válidos — como na Rodada 1
- ✅ Chave nunca em log, erro ou resultado / Verificação 7 — como na Rodada 1
- ✅ Testes nunca chamam o OpenRouter — `no_real_llm`; grep vazio
- ✅ Verificação 8 — como na Rodada 1
- ✅ FR-001, FR-002, FR-004, FR-005, FR-006 — como na Rodada 1
- ✅ FR-003 — esquema estrito com frase repetida provada sob `reorder=true`; nova tentativa com o motivo; `llm_error`
- ✅ 2.1.b.3 — como na Rodada 1
- ✅ Constituição §I, §III, §VI / ADR-0010 — como na Rodada 1; §III "mesmas mensagens e o que estava errado" agora provado
- ✅ Verificação 9 — pytest, ruff, mypy e `uv lock --check` verdes

### Veredito geral: PASS
Os dois PARCIAL da Rodada 1 (Passo 2 e Passo 4 b) fecharam com teste e mutação vermelha; todos os
passos `[x]` PASS, critérios cobertos, suítes e checagens verdes.
