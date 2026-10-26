# QA — 1.1.i.1 — Consultar e baixar exportações (`render list/show/download`)

## Plano de QA — 2026-10-26

**baseline_commit**: 593a41c0c4e1b851d3ff692f0f62c9172056bcee
**Componentes em escopo**:
- core: `packages/core/src/wordcut/service/renders.py` (novo), `packages/core/src/wordcut/db/renders.py`
  (consulta da mais recente para a mais antiga), reaproveitando `service/rendering.py::show_render`,
  `service/cuts.py::shown_render`/`existing_cut`, `sermon_folder.folder_name` e
  `files.copy_without_overwrite`;
- cli: `apps/cli/src/wordcut_cli/render.py` (novo), `apps/cli/src/wordcut_cli/__init__.py`;
- docs: `CHANGELOG.md`, `docs/cli.md` §9.

**Suítes que valem como prova**:
- core: `uv run pytest packages/core/tests -q` (arquivo do passo: `packages/core/tests/test_renders_service.py`);
- cli: `uv run pytest apps/cli/tests -q` (arquivo do passo: `apps/cli/tests/test_render_command.py`);
- completa: `uv run pytest -q`;
- checagem estática: `uv run ruff check . && uv run ruff format --check . && uv run mypy`.

### Divergências do plan.md com o código no baseline

O plan.md foi escrito antes dos itens 6 (`sermon download`) e 15 (`cut render`). A barra abaixo
já considera o código real. Recomendação para cada divergência:

| # | O plan.md diz | O código no baseline tem | Recomendação (a barra cobra isto) |
|---|---|---|---|
| D1 | Criar `show_render(conn, home, render_id)` em `service/renders.py` | `show_render` já existe em `service/rendering.py:85` (mesma assinatura, `not_found` com `{"render_id"}`), usado por `cut render` (`apps/cli/src/wordcut_cli/cut.py:223`) e por `test_render_task.py` | Não duplicar. `service/renders.py` ganha só `list_renders` e `render_video`; `render show` chama o `show_render` existente. Mover a função só se todos os imports forem ajustados no mesmo passo e a suíte seguir verde. |
| D2 | Alterar `db/renders.of_cut` para "mais recente primeiro" | `of_cut` é da mais antiga para a mais nova (`ORDER BY id`) e alimenta `cut show` (`service/cuts.py:273`), que `docs/cli.md:469` documenta como "da mais antiga para a mais nova" | Não inverter `of_cut`. Criar consulta própria (ex.: `newest_of_cut`) com `ORDER BY created_at DESC, id DESC`, ou ordenar no serviço. Inverter `of_cut` quebra o contrato do `cut show`, e nenhum teste atual pegaria isso (ver L1). |
| D3 | Alterar `db/renders.by_id` | `by_id` já existe (`db/renders.py:51`) e tem teste (`test_renders_repository.py:82`) | Nada a fazer. |
| D4 | `render_video(...) -> (path, suggested_name)` (tupla) | O item 6 usa `SermonVideo(path, suggested_name)` (dataclass) em `service/sermons.py:176` | Devolver um tipo nomeado no mesmo formato (dataclass própria ou genérica), não uma tupla. |
| D5 | "reaproveita `files.copy_without_overwrite`", sem assinatura | `copy_without_overwrite(source: Path, destination: str \| PathLike, suggested_name: str) -> Path` (`files.py:21`); a CLI do item 6 chama assim e devolve `{"path", "bytes"}` (`sermon.py:238-243`) | `render download` repete o `_download` do `sermon`: `copy_without_overwrite(video.path, args.output, video.suggested_name)`, `-o/--output` com padrão `os.curdir` e a mesma ajuda, saída `{"path": <absoluto>, "bytes": <tamanho>}` e, sem `--json`, só o caminho. |
| D6 | "Arquivo ausente → `internal_error` com `{"render_id": N}`" | Padrão do item 6: mensagem sem o caminho da pasta de dados (`sermons.py:198-207`) | Mensagem do tipo "Arquivo da exportação N não encontrado.", `details == {"render_id": N}`, sem `WORDCUT_HOME` na saída. |
| D7 | Nome legível = `folder_name(data do culto, título do corte)` | `folder_name(service_date, title, reference=None)`; `sermon_video` exige pregação `processed` | `render_video` lê o corte (`existing_cut`) e a data do culto da pregação do corte, sem `reference` e sem exigir `processed` (a exportação já existe; não inventar `sermon_not_processed`). |
| D8 | Opções na lista: "resumo das opções" (spec) | A tarefa `render` já grava `options.summary(...)` em `renders.options` (`tasks/render.py:64`) | O item de `render list` é o mesmo objeto de `render show` (`shown_render`): `id, cut_id, path, duration, created_at, options`. Não recalcular o resumo. |

### Matriz por passo

| Passo (plan.md) | O que precisa ser provado | Como |
|---|---|---|
| 1 — Serviço (listar, detalhar, localizar) | (a) `list_renders` devolve `{"items": [...]}` do corte da mais recente para a mais antiga, com empate de `created_at` decidido por `id DESC`; (b) cada item no formato de `shown_render`, `path` absoluto e `options` como gravadas; (c) corte inexistente → `not_found` com `{"cut_id"}`; corte sem exportações → `{"items": []}`; (d) `show_render` reaproveitado: exportação inexistente → `not_found` com `{"render_id"}`; (e) `render_video` dá o arquivo existente e o nome `AAAA-MM-DD - <título do corte>.mp4`, com título do corte diferente do da pregação e caracteres proibidos removidos; (f) arquivo ausente → `internal_error`, `details == {"render_id": N}`, mensagem sem `home.root`; (g) tudo funciona com a trava de processamento tomada por outro processo; (h) `cut show` continua da mais antiga para a mais nova | Testes de comportamento em `packages/core/tests/test_renders_service.py` pela interface pública do serviço, com banco real em pasta temporária e linhas criadas por `db.renders.insert` + arquivo em `home.cut_media(cut_id)`; trava via fixture `lock_owner` (`conftest.py:115`). (h) por teste com duas exportações no `show_cut` (novo ou em `test_cuts_service.py`). Mutações exigidas no `tdd.md`. Suíte core verde. |
| 2 — CLI (`render list/show/download`) | (a) grupo `render` registrado em `wordcut_cli/__init__.py`; (b) `render list --cut <id> --json` → `{"items": [...]}` mais recente primeiro; `--cut` ausente → erro de uso, saída 2; (c) `render show <id> --json` → `{id, cut_id, path, duration, created_at, options}` com `path` absoluto; (d) `render download <id>` na pasta atual cria `AAAA-MM-DD - Título.mp4` com bytes idênticos e devolve `{path, bytes}`; sem `--json` imprime só o caminho; (e) segundo download → ` (2)`, primeiro intacto; `-o` arquivo cria pastas; `-o` pasta existente ou terminada em `/` recebe o nome legível; (f) `not_found` → saída 3; arquivo ausente → `internal_error`, saída 1, sem `WORDCUT_HOME` no stdout; ID não numérico → saída 2; (g) os três comandos funcionam com a trava tomada; (h) `--json` antes ou depois da ação | Testes em `apps/cli/tests/test_render_command.py` via `main([...])` e `capsys`, no molde de `test_sermon_download_command.py` (mesmos casos, mesmos códigos de saída). Suíte cli verde. |
| 3 — Documentação | `CHANGELOG.md` em `[Não lançado] / Adicionado` cita `render list --cut`, `render show` e `render download [-o]`; `docs/cli.md` §9 diz a ordem (mais recente primeiro), o formato dos itens e a saída `{path, bytes}` do `download`; `docs/cli.md:469` (`cut show`, mais antiga primeiro) intocado | Inspeção de `git diff 593a41c -- CHANGELOG.md docs/cli.md`, conferida contra o comportamento que os testes dos passos 1 e 2 provam. |

### Matriz por critério de aceite

| Critério de aceite | O que o cobre |
|---|---|
| Spec · Cenário "histórico do corte": duas exportações, `render list --cut <id> --json` → `{"items"}` da mais recente para a mais antiga, com `id, cut_id, duration, created_at` e opções | Passo 2 (b) na CLI + Passo 1 (a, b); mutação de ordem vermelha |
| Spec · Cenário "detalhar": `render show <id> --json` → `{id, cut_id, path, duration, created_at, options}`, `path` absoluto | Passo 2 (c) + Passo 1 (b, d); `Path(path).is_absolute()` e `read_bytes()` do arquivo |
| Spec · Cenário "baixar": `2026-10-18 - Graça que alcança.mp4` na pasta, idêntico, sem sobrescrever, saída com o caminho | Passo 2 (d, e) com corte titulado "Graça que alcança" de pregação de 2026-10-18 (dados fictícios) |
| Borda: corte ou exportação inexistente → `not_found` | Passo 1 (c, d) + Passo 2 (f) com saída 3 nos três comandos |
| Borda: arquivo ausente → `internal_error` sem caminho interno | Passo 1 (f) + Passo 2 (f) (`download`); `show` não abre o arquivo (ver L4) |
| Borda: `-o` com as regras do `sermon download` (pasta, ` (2)`) | Passo 2 (e) |
| Borda: nenhum comando pega a trava | Passo 1 (g) + Passo 2 (g) com `lock_owner` |
| FR-001 | = Cenário "histórico do corte" |
| FR-002 | = Cenário "detalhar" |
| FR-003 | = Cenário "baixar" + borda `-o` |
| Verificação · `render list --cut <id> --json` mais recente primeiro; corte inexistente → `not_found` | Passo 2 (b, f) |
| Verificação · `render show <id> --json` com `path` absoluto | Passo 2 (c) |
| Verificação · `render download <id>` nome legível, bytes idênticos, sem sobrescrever; `-o` como no item 6 | Passo 2 (d, e) |
| Verificação · arquivo ausente → `internal_error` sem caminho; sem trava | Passo 1 (f, g) + Passo 2 (f, g) |
| Verificação · quality gates limpos | `uv run pytest -q` e `uv run ruff check . && uv run ruff format --check . && uv run mypy` verdes |

### Lacunas do plan.md (o que fica PARCIAL sem a correção)

- **L1** — Ordem do `cut show` sem proteção: nenhum teste tem duas exportações no `cut show`. Se o
  passo 1 inverter `of_cut` (D2), a suíte segue verde e o contrato de `docs/cli.md:469` quebra.
  Sem teste do `cut show` com duas exportações, o passo 1 fica PARCIAL.
- **L2** — Empate de `created_at`: a tarefa grava em segundos (`microsecond=0`), então duas
  exportações no mesmo segundo são reais. Sem teste com `created_at` igual que cobre o `id DESC`,
  o passo 1 fica PARCIAL.
- **L3** — Saída do `download` e itens do `list` sem formato no plano e no §9. A barra adota
  `{path, bytes}` (D5) e o formato de `shown_render` (D8). Contrato diferente sem atualizar
  `docs/cli.md` §9 deixa os passos 2 e 3 PARCIAL.
- **L4** — `render show` com o arquivo ausente: a spec não diz se dá erro. A barra é conservadora:
  `show` devolve o registro sem abrir o arquivo (como hoje faz `show_render`); só o `download`
  dá `internal_error`.
- **L5** — `path` "absoluto" depende de `WORDCUT_HOME` absoluto: `shown_render` faz
  `home.root / row.path` sem `.absolute()` (`service/cuts.py:285`), e `Home.from_environment`
  aceita caminho relativo. Fora da barra desta issue; registrar se aparecer.
- **L6** — Pregação não processada: `render_video` não deve chamar `sermon_video` (exige
  `processed` e devolve o vídeo da pregação, não o da exportação). Reusar `sermon_video` é FAIL
  no passo 1 (e).

---

## Rodada 1 — 2026-10-26 — working tree sobre 593a41c

**baseline_commit**: 593a41c0c4e1b851d3ff692f0f62c9172056bcee
**Componentes avaliados**: core (`service/renders.py`, `db/renders.py`, `service/cuts.py`,
`service/rendering.py`), cli (`render.py`, `__init__.py`, `cut.py`), docs (`CHANGELOG.md`,
`docs/cli.md` §9)
**Suítes**: core ✅ (802 / 0 falhas) · cli ✅ (401 / 0 falhas) · completa ✅ (1204 / 0 falhas)
· ruff check ✅ · ruff format --check ✅ · mypy ✅

**Barra aplicada**: matriz do topo + decisões do orquestrador no plan.md (D1–D8, L1–L6), com
L5 dentro da barra (`path` sempre absoluto, mesmo com `WORDCUT_HOME` relativo).

**Mutações** (cópia no scratchpad; código do repositório intocado): 9 de 9 mortas — as exigidas
(ordem DESC→ASC, sem desempate `id DESC`, `of_cut` invertido, título da pregação no lugar do
corte, `shutil.copyfile` sobrescrevendo, sem `is_file`, `download` dentro da trava) mais
`shown_render` sem `.absolute()` (L5) e caminho errado do arquivo em `render_video`.

**Comentários**: conformes a CONTRIBUTING.md §5 (`service/renders.py:58` é intenção com
referência; demais são docstrings de contrato; o comentário de `VIDEO` nos testes repete o
padrão de `test_sermon_download_command.py:27`).

### Veredito por passo

| Passo (plan.md) | Veredito | Evidência / motivo |
|---|---|---|
| 1 — Serviço | PASS | 1a–1g em `test_renders_service.py` (12 testes), 1h em `test_cuts_service.py::test_shown_cut_lists_its_exports_the_oldest_first`; D1 (`show_render` reusado via `existing_render`), D2 (`newest_of_cut`, `of_cut` intocado), D4 (`RenderVideo`), D6, D7/L6 (sem `sermon_video`, sem `processed`), D8, L1, L2, L4, L5 atendidos; mutações M1–M4, M6, M8, M9 mortas |
| 2 — CLI | PASS | 2a–2h em `test_render_command.py` (21 casos) e `test_cli.py` (`--help` com `render`); D5 (`_download` igual ao do `sermon`, `{path, bytes}`, só o caminho sem `--json`); saídas 2/3/1; stdout sem `WORDCUT_HOME`; mutações M5, M7 mortas |
| 3 — Documentação | PASS | `CHANGELOG.md` [Não lançado]/Adicionado cita `render list --cut`, `render show`, `render download [-o]`, e Alterado o `path` absoluto; `docs/cli.md` §9 com ordem, formato dos itens e `{path, bytes}`; §8.2 (`renders` da mais antiga para a mais nova) intocado; texto confere com o que os testes provam (L3) |

### Critérios de aceite
- ✅ Cenário "histórico do corte" / FR-001 — `test_list_with_json_gives_the_exports_of_the_cut_the_most_recent_first` + `test_a_listed_export_is_given_as_render_show_gives_it_with_its_options_as_recorded`, `test_exports_recorded_in_the_same_second_are_listed_the_last_recorded_first`
- ✅ Cenário "detalhar" / FR-002 — `test_show_with_json_gives_the_export_with_the_absolute_path_of_its_file`, `test_show_with_a_relative_data_folder_gives_the_absolute_path_of_the_file`
- ✅ Cenário "baixar" / FR-003 — `test_download_with_json_copies_the_export_to_the_current_folder_with_the_readable_name`, `test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file`
- ✅ Borda: corte ou exportação inexistente → `not_found` — `test_list_of_a_cut_that_does_not_exist_fails_with_not_found_and_exit_3`, `test_an_export_that_does_not_exist_fails_with_not_found_and_exit_3[show|download]` + testes de serviço
- ✅ Borda: arquivo ausente → `internal_error` sem caminho — `test_download_of_an_export_whose_file_left_the_disk_is_the_service_internal_error`, `test_an_export_whose_file_left_the_disk_has_no_video_and_says_so_without_the_data_folder`
- ✅ Borda: `-o` com as regras do `sermon download` — `test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path`, `test_download_to_a_folder_writes_the_readable_name_inside_it`
- ✅ Borda: nenhum comando pega a trava — `test_list_show_and_download_work_while_another_process_holds_the_processing_lock` + teste de serviço com `lock_owner`
- ✅ Verificação · quality gates — `uv run pytest -q` (1204), ruff check, ruff format --check, mypy limpos

### Veredito geral: PASS
Os 3 passos PASS, os 8 critérios cobertos, suítes e checagens verdes, 9 de 9 mutantes mortos.
