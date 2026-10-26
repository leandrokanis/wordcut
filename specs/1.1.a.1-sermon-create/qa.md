# QA — 1.1.a.1 — Criar pregação pelo link e consultá-la (`sermon create`, `list`, `show`)

## Plano de QA — 2026-10-26

**baseline_commit**: 9b8d7204d7d3fba9d79408794888db72de32bf58
**Componentes em escopo**: `packages/core` (`wordcut.youtube`, `wordcut.config`,
`wordcut.db` + migração 0002, `wordcut.db.sermons`, `wordcut.service.sermons`), `apps/cli`
(`wordcut_cli.contract`, `wordcut_cli.deps`, `wordcut_cli.sermon`, `wordcut_cli.__init__`),
`docs/architecture/README.md` §4, `CHANGELOG.md`.
**Suítes que valem como prova**: Python (core, cli) — `uv run pytest -q`; por arquivo
`uv run pytest <arquivo> -q`; checagem estática
`uv run ruff check . && uv run ruff format --check . && uv run mypy`.

Regras da barra (valem para todos os passos):

- Nenhum teste chama o YouTube de verdade: no core, `subprocess.run` de `wordcut.youtube` é
  substituído; na CLI, `wordcut_cli.deps.live_source` é substituído por um dublê que conta as
  chamadas. Teste que alcance o `yt-dlp` real é FAIL do passo.
- Testes da CLI usam o fixture `wordcut_home` (nunca o `~/.local/share/wordcut` real).
- Teste de comportamento pela interface pública (`video_id`, `YouTube.info`, `connect`,
  repositório, funções do serviço, `wordcut_cli.main`); teste que só confere chamada interna
  conta como frágil (PARCIAL).
- Mutação que sobreviver em regra listada como "exige" deixa o passo PARCIAL.

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — ID do vídeo e erros do YouTube | (a) `video_id` extrai o mesmo ID de `watch?v=` (com `&t=`/`&list=`), `youtu.be/<id>?si=`, `/live/<id>?feature=`, `/shorts/<id>`, com `https`/`http` e com ou sem `www.`/`m.`; (b) link de outro host (inclusive `youtube.com.<outro>.example`), YouTube sem ID (`youtube.com/`, `watch?v=`) e texto que não é URL → `WordcutError` `invalid_argument`, saída 2, `details == {"argument": "link"}`; (c) `YouTube.info` traduz falha do `yt-dlp` (`CalledProcessError`), JSON inválido e vídeo sem horário de início em `YouTubeError`, com mensagem em português sem o comando nem o caminho dos cookies; (d) `config_dir()` = `WORDCUT_CONFIG` quando definido, senão `~/.config/wordcut`; `youtube_cookies()` = `<config_dir>/youtube-cookies.txt`; `YouTube()` sem argumento usa esse caminho em `base_command()`; (e) testes antigos de `test_youtube.py` seguem verdes | `packages/core/tests/test_video_id.py` parametrizado por tabela (aceitos e rejeitados); `test_youtube.py` com `monkeypatch` de `subprocess.run` em `wordcut.youtube` e arquivo de cookies em `tmp_path`; `monkeypatch.setenv("WORDCUT_CONFIG")`/`HOME`. Exige mutações: aceitar qualquer host em `video_id` → vermelha; remover a tradução de `CalledProcessError` → vermelha; `DEFAULT_COOKIES` fixo em `~/.config` ignorando `WORDCUT_CONFIG` → vermelha |
| 2 — Tabela e repositório | (a) `connect` num `Home` novo deixa `user_version = 2` e a tabela `sermons`; banco já em `user_version = 1` migra para 2 sem perder `app_info`; (b) `insert` → `by_id` e `by_youtube_id` devolvem o mesmo `SermonRow` (todos os campos da entidade do spec); (c) `youtube_id` repetido → `sqlite3.IntegrityError`; (d) `status` fora de `created/trimmed/processing/processed/failed` → `IntegrityError`; (e) `list(None)` ordena por `service_date DESC, id DESC`; `list(status)` filtra; ID inexistente → `None` | Testes de integração com SQLite real em `tmp_path` (`wordcut_home`), pela API do repositório; em `packages/core/tests/test_sermons_service.py` ou arquivo próprio do repositório. Exige mutações: tirar o `UNIQUE` → vermelha; tirar o `CHECK` → vermelha; `ORDER BY ... ASC` ou sem `id DESC` no desempate → vermelha |
| 3 — Serviço de pregações | (a) `create_sermon` novo → `dict` com `id` (int), `youtube_id`, `url`, `title`, `service_date` (`AAAA-MM-DD`), `live_duration` (número, segundos), `live_finished: true`, `status: "created"`, `created: true`, `created_at` ISO 8601 com fuso; (b) mesmo vídeo por outro formato de link → `created: false`, mesmo `id`, dublê chamado 1 vez no total; (c) live no ar → `live_finished: false`; (d) link inválido → `invalid_argument` e dublê com 0 chamadas; (e) dublê lança `YouTubeError` → `WordcutError` `youtube_error` (saída 6) e nenhuma linha gravada; (f) corrida: dublê que grava o mesmo `youtube_id` durante `info()` → `created: false`, mesmo `id`, sem exceção; (g) `list_sermons` → `{"items": [...]}` mais recente primeiro, filtro por `status`, contagens de cortes zeradas; (h) `show_sermon` → pregação + `live_start`/`live_end` `null` + `cuts: []`; ID inexistente → `not_found` (saída 3); (i) serviço sem `argparse`, `print` ou import de `wordcut_cli` (ADR-0004) | `packages/core/tests/test_sermons_service.py` com dublê de `LiveSource` (classe com `info(url)` que conta chamadas) e SQLite real em `tmp_path`; (i) por leitura do diff. Exige mutações: remover a busca por `youtube_id` antes de `info()` → vermelha (dublê chamado 2 vezes); remover o tratamento de `IntegrityError` → vermelha; ignorar o filtro `status` → vermelha; não traduzir `YouTubeError` → vermelha (vira exceção crua) |
| 4 — CLI `sermon` | (a) `wordcut sermon create <link> --json` → saída 0 e exatamente um documento JSON no stdout com os campos de 3a; (b) `--json` aceito antes de `sermon`, entre `sermon` e a ação, e depois da ação, com o mesmo resultado; (c) live no ar → aviso no stderr, stdout só com o JSON; com `--quiet` o aviso continua (`Context.warn` não é suprimido); (d) erros pelo contrato: link inválido → 2 com `details.argument == "link"`; `youtube_error` → 6; `sermon show 999` → 3; `sermon show abc` → 2; `sermon list --status x` → 2; `sermon` sem ação → 2; com `--json` o erro é `{"error": {...}}` no stdout, sem `--json` stdout vazio e `erro: <message>` no stderr; (e) sem `--json`, stdout em português com ID, título, data e duração (create/show) e uma linha por pregação (list), stderr vazio no sucesso; (f) `sermon --help` lista `create`, `list`, `show`; o `--help` de cada ação traz um exemplo `wordcut sermon ...` com dados fictícios; (g) `wordcut --help` lista `sermon` (`test_cli.py`); (h) `test_legacy_commands.py`, `test_cli_contract.py` e `test_status_command.py` seguem verdes | `apps/cli/tests/test_sermon_command.py` via `wordcut_cli.main(argv)` com `capsys`, `wordcut_home` e `monkeypatch` de `wordcut_cli.deps.live_source`; `apps/cli/tests/test_cli.py`; suíte completa da CLI. Exige mutações: `warn` respeitando `--quiet` → vermelha; `warn` no stdout → vermelha; `add_group` sem repetir as opções globais → vermelha (posição intermediária de `--json`) |
| 5 — Documentação | `docs/architecture/README.md` §4 registra `service.sermons` e os comandos `sermon create/list/show` como existentes; `CHANGELOG.md` tem a entrada; nenhuma ADR aceita foi editada; texto em português | Leitura do diff contra o baseline (`git diff 9b8d720 -- docs CHANGELOG.md`); sem teste automatizado |

| Critério de aceite | O que o cobre |
|---|---|
| Cenário "criar pela primeira vez" (spec) / Verificação 1 / FR-001 | Passo 3a (serviço) e 4a (CLI, JSON e saída 0); `id` inteiro e estável conferido relendo por `sermon show <id>` |
| Cenário "mesmo vídeo de novo" (spec) / Verificação 2 / FR-002 | Passo 1a (tabela de formatos) + 3b (dublê 1 chamada, mesmo `id`) + 4a com dois links de formatos diferentes; corrida em 3f |
| Cenário "live ainda no ar" (1.1.a.2) / Verificação 3 / FR-003 | Passo 3c (`live_finished: false`) + 4c (aviso no stderr, também com `--quiet`) |
| Cenário "listar" / Verificação 6 / FR-004 | Passo 2e + 3g (ordem `service_date DESC, id DESC`, filtro) + 4a/4e para `sermon list --json` e texto |
| Cenário "detalhar" / Verificação 7 / FR-005 | Passo 3h + teste CLI de `sermon show <id> --json` com bordas `null` e `cuts: []` |
| Borda: link não YouTube ou sem ID → `invalid_argument` (2), sem consultar o YouTube / Verificação 4 | Passo 1b + 3d (0 chamadas no dublê) + 4d (saída 2 e `details.argument`) |
| Borda: falha do YouTube → `youtube_error` (6), nada criado / Verificação 5 | Passo 1c + 3e (nenhuma linha) + 4d (saída 6); mensagem sem caminho de cookies (1c) |
| Borda: `sermon show` de ID inexistente → `not_found` (3) / Verificação 7 | Passo 3h + 4d |
| Borda: vídeo sem horário de início → `youtube_error` com mensagem clara | Passo 1c (metadado sem `release_timestamp`/`timestamp` → `YouTubeError`) + 3e |
| Borda: sem `--json`, resumo legível em português / Verificação 8 | Passo 4e |
| FR-006 — contrato docs/cli.md §4 e §5 | Passo 4b, 4c, 4d (um documento JSON, canais, códigos de erro e saídas) |
| FR-007 — regra no serviço, CLI só traduz (ADR-0004) | Passo 3i (leitura do diff) + testes de serviço que cobrem toda a regra sem a CLI |
| Pressuposto: cookies de `WORDCUT_CONFIG` e nunca em saída | Passo 1c e 1d |
| Verificação 9 — quality gates limpos | `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy` |

### Lacunas do plano (decididas pela opção mais conservadora; execução automatizada)

1. **Duração de live em andamento.** `LiveInfo.from_metadata` exige `metadata["duration"]`
   como número; o plano não diz o que fazer quando o `yt-dlp` não traz a duração (ausente ou
   `null`), o que pode acontecer justamente com live no ar (pressuposto, não verificado). Sem
   decisão, o cenário 1.1.a.2 pode cair em `internal_error`. Barra: teste com metadado
   `live_status: "is_live"` sem `duration` → criação com `live_finished: false` e
   `live_duration: null`. Sem esse teste, o critério 1.1.a.2 fica PARCIAL.
2. **Cookies ausentes.** `YouTube._run` lança `FileNotFoundError` com o caminho; o plano não o
   inclui entre as falhas traduzidas, então vira `internal_error` (1). Barra: arquivo de
   cookies ausente → `youtube_error` (6) com mensagem em português sem o caminho. Sem isso,
   passo 1 PARCIAL.
3. **Cookies resolvidos na importação.** "`DEFAULT_COOKIES` passa a vir de
   `config.youtube_cookies()`" calculado na importação ignora `WORDCUT_CONFIG` definido
   depois. Barra: resolução no momento da construção do `YouTube`, provada por
   `monkeypatch.setenv` depois da importação (passo 1d).
4. **Formato das contagens de cortes.** O plano diz "contagens zeradas por estado" sem nome
   de campo. Barra: um objeto com as três chaves de docs/cli.md §8 (`suggested`, `chosen`,
   `discarded`), todas 0, em `list` e `show`, com nome de campo registrado no plano (sugestão:
   `cut_counts`). Sem nome decidido, FR-004 fica PARCIAL.
5. **Campos de docs/cli.md §7.2 omitidos.** O `list` deve trazer a duração da pregação e o
   `show` a última tarefa; spec e plano omitem. Barra: `duration: null` (até o `trim`) e
   `last_task: null` (até existirem tarefas), ou a omissão registrada no plano como adiada.
   Sem um dos dois, FR-004/FR-005 ficam PARCIAL.
6. **Validação do ID e do host.** O plano não diz se o ID tem formato validado nem como o host
   é comparado. Barra: host em lista exata (`youtube.com`, `www.youtube.com`,
   `m.youtube.com`, `youtu.be`), ID `[A-Za-z0-9_-]{11}`; `youtube.com.<outro>.example` e ID
   vazio são rejeitados (passo 1b).
7. **Prova da corrida.** O plano decide `IntegrityError` → reler, mas não como testar. Barra:
   dublê cujo `info()` insere o mesmo `youtube_id` antes de devolver (passo 3f).
8. **Valores de `--status`.** Não decidido se o `argparse` restringe. Barra: `choices` com os
   cinco estados; valor fora → `invalid_argument` (2) com `details.argument`.
9. **Guarda contra rede.** Nada impede um teste novo de alcançar o `yt-dlp` real (a fábrica
   padrão `deps.live_source()` devolve o `YouTube`). Barra: fixture `autouse` na suíte da CLI
   que troca `deps.live_source` por um dublê que falha se não for substituído, e
   `subprocess.run` substituído em todo teste de `YouTube.info`.
10. **Relógio do `created_at`.** Sem injeção decidida; teste que compare o dicionário inteiro
    fica instável. Barra: `created_at` conferido por formato (ISO 8601 com fuso) ou parâmetro
    `now` como em `service.status.machine_status`.
11. **Comando anterior `info`.** `YouTube.info` passa a lançar `YouTubeError` no lugar de
    `CalledProcessError`/`ValueError`; o comando `info` da CLI anterior muda de erro em
    execução. Barra: `test_legacy_commands.py` verde; nenhuma exigência nova sobre ele.

## Rodada 1 — 2026-10-26 — working tree sobre 9b8d720

**baseline_commit**: 9b8d7204d7d3fba9d79408794888db72de32bf58
**Componentes avaliados**: `packages/core`, `apps/cli`, `docs/architecture/README.md`, `CHANGELOG.md`
**Suítes**: Python (core, cli, api) ✅ (250 / 0 falhas) · `ruff check` ✅ · `ruff format --check` ✅ · `mypy` ✅ (44 arquivos)

Mutações manuais numa cópia da árvore no scratchpad (a worktree não foi tocada): 31 de 31
mortas (passo 1: 12, passo 2: 5, passo 3: 8, passo 4: 6). Todas as mutações que a matriz
exige estão entre elas.

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — ID do vídeo e erros do YouTube | PASS | `test_video_id.py` (10 aceitos, 14 rejeitados, incluindo `youtube.com.golpe.example`, ID curto ou longo e `ftp://`); `test_youtube.py` com `subprocess.run` substituído por fixture `autouse`: `CalledProcessError`, JSON inválido, vídeo sem horário e cookies ausentes viram `YouTubeError` sem o comando nem o caminho; `test_config.py` e `test_youtube_without_cookies_argument_uses_the_secrets_folder_set_after_import` (decisão 3); live sem `duration` (decisão 1) |
| 2 — Tabela e repositório | PASS | `test_sermons_repository.py` com SQLite real: `user_version` 2, migração de 1 para 2 mantendo `app_info`, releitura de todos os campos, `UNIQUE`, `CHECK`, ordem `service_date DESC, id DESC`, filtro. A função de listagem chama `newest_first`, não `list` como no Contexto de código; só o nome diverge |
| 3 — Serviço de pregações | PASS | `test_sermons_service.py`: dicionário completo com `now` injetado (decisão 10), outro formato de link com `created: false` e 1 chamada, live no ar com `live_duration: null`, link inválido com 0 chamadas, `youtube_error` (6) sem linha gravada, corrida pelo dublê `RacedLive` (decisão 7), `cut_counts` (decisão 4), `duration` e `last_task` nulos (decisão 5), `not_found` (3). `service/sermons.py` sem `argparse`, `print` nem `wordcut_cli` |
| 4 — CLI `sermon` | PASS | `test_sermon_command.py` (25 casos): JSON único no stdout, `--json` antes, entre e depois, aviso no stderr com e sem `--quiet`, erros 2/3/6 pelo contrato com `details.argument` (`link`, `id`, `--status` por `choices`, `action`), stdout vazio e `erro:` sem `--json`, textos em português, `--help` com exemplos; `test_cli.py` lista `sermon`; `conftest.py` com fixture `autouse` que recusa o YouTube (decisão 9); testes antigos verdes (decisão 11) |
| 5 — Documentação | PASS | `git diff 9b8d720 -- docs CHANGELOG.md`: §4 registra `service.sermons`, `db.sermons`, `config` e `sermon create/list/show`; CHANGELOG em Adicionado e Alterado; nenhuma ADR editada |

Fato relatado pelo implementador, julgado: a troca de `test_missing_cookies_file_is_explained`
(esperava `FileNotFoundError`) por `test_missing_cookies_file_is_a_youtube_error_explained_without_its_path`
contradiz a letra da matriz 1(e) ("testes antigos seguem verdes"), mas a decisão 2 exige o
contrário para esse caso, e a decisão 2 é posterior e específica. O teste novo mantém o
que o antigo provava (a mensagem fala de cookies) e acrescenta a ausência do caminho.
Aceito; a matriz 1(e) não serve para julgar esse teste, e o passo segue PASS.

Política de comentários (CONTRIBUTING.md §5): os 5 comentários novos estão em inglês e
são de tipos aceitos (intenção, referência a docs/cli.md, restrição do `yt-dlp`);
docstrings novas são de contrato público.

Fora da barra, sem efeito no veredito: `video_id` compara o host com maiúsculas e minúsculas
e não aceita porta nem barra final (`youtu.be/<id>/`); a matriz não pede esses casos.

### Critérios de aceite
- ✅ Criar pela primeira vez / Verificação 1 / FR-001 — `test_first_sermon_of_a_finished_live_is_created_with_the_live_data`, `test_create_with_json_prints_the_new_sermon_and_exits_0`, `test_show_with_json_prints_the_sermon_with_empty_borders_and_no_cuts` (relê o `id`)
- ✅ Mesmo vídeo de novo / Verificação 2 / FR-002 — `test_every_link_format_of_the_same_video_gives_its_id`, `test_same_video_through_another_link_returns_the_existing_sermon_without_asking_youtube`, `test_same_video_through_another_link_returns_the_existing_sermon` (CLI), `test_create_that_loses_a_race_for_the_same_video_returns_the_winner`
- ✅ Live ainda no ar / Verificação 3 / FR-003 — `test_live_still_on_air_without_duration_is_created_unfinished_with_unknown_duration`, `test_live_still_on_air_warns_on_stderr_even_when_quiet_and_stdout_keeps_only_the_json`
- ✅ Listar / Verificação 6 / FR-004 — `test_sermons_come_newest_service_first_and_the_later_one_first_on_the_same_day`, `test_sermons_are_listed_newest_service_first_with_zeroed_cut_counts`, `test_list_with_json_prints_the_items_newest_service_first`, `test_list_with_status_keeps_only_the_sermons_in_that_state`, `test_list_without_json_prints_one_line_per_sermon_newest_first`
- ✅ Detalhar / Verificação 7 / FR-005 — `test_shown_sermon_has_empty_borders_no_task_and_no_cuts`, `test_show_with_json_prints_the_sermon_with_empty_borders_and_no_cuts`
- ✅ Link não YouTube ou sem ID → `invalid_argument` (2), sem consultar o YouTube / Verificação 4 — `test_link_that_does_not_name_a_youtube_video_is_an_invalid_argument`, `test_link_without_a_video_is_refused_before_asking_youtube`, `test_sermon_failures_follow_the_error_contract[link]`
- ✅ Falha do YouTube → `youtube_error` (6), nada criado / Verificação 5 — `test_failed_yt_dlp_call_is_a_youtube_error_that_hides_the_command_and_cookies`, `test_youtube_failure_is_a_youtube_error_and_creates_nothing`, `test_youtube_failure_exits_6_and_creates_nothing`
- ✅ `sermon show` de ID inexistente → `not_found` (3) — `test_showing_an_unknown_sermon_is_not_found`, `test_sermon_failures_follow_the_error_contract[999]`, `test_failure_without_json_leaves_stdout_empty_and_explains_on_stderr`
- ✅ Vídeo sem horário de início → `youtube_error` com mensagem clara — `test_video_without_start_time_is_a_youtube_error_that_says_so` + tradução do serviço
- ✅ Sem `--json`, resumo em português / Verificação 8 — `test_create_without_json_summarizes_the_sermon_in_portuguese`, `test_list_without_json_*`, `test_show_without_json_describes_the_sermon_in_portuguese`
- ✅ FR-006 — contrato docs/cli.md §4 e §5 — `test_json_option_is_accepted_before_between_and_after_the_sermon_action`, `test_sermon_failures_follow_the_error_contract`, teste do aviso
- ✅ FR-007 — regra no serviço (ADR-0004) — leitura do diff + `test_sermons_service.py` cobre a regra sem a CLI
- ✅ Pressuposto: cookies de `WORDCUT_CONFIG` e nunca em saída — `test_config.py`, `test_youtube_without_cookies_argument_uses_the_secrets_folder_set_after_import`, `test_missing_cookies_file_is_a_youtube_error_explained_without_its_path`
- ✅ Verificação 9 — quality gates — 250 passed; ruff e mypy limpos

### Veredito geral: PASS
Os 5 passos estão PASS, os 14 critérios cobertos e as suítes e checagens verdes. As 31 mutações, incluindo todas as exigidas, foram mortas.
