# Plan: Consultar e baixar exportações

**Issue**: 1.1.i.1
**Feature**: specs/1.1.i.1-render-download
**Data**: 2026-10-26

---

## Resumo

Serviço `renders` (listar por corte, detalhar, localizar o arquivo com nome legível) e grupo
`render` na CLI, reaproveitando a cópia sem sobrescrever do item 6.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/service/renders.py` — `RenderVideo(path, suggested_name)` (formato de `SermonVideo`), `existing_render(conn, render_id)`, `list_renders(conn, home, cut_id)`, `render_video(conn, home, render_id) -> RenderVideo` |
| Reusar | `packages/core/src/wordcut/service/rendering.py::show_render` (já existe; passa a usar `existing_render`), `service/cuts.py::existing_cut`, `sermon_folder.folder_name`, `files.copy_without_overwrite` |
| Alterar | `packages/core/src/wordcut/service/cuts.py::shown_render` — `path` absoluto mesmo com `WORDCUT_HOME` relativo |
| Alterar | `packages/core/src/wordcut/db/renders.py` — nova `newest_of_cut` (`created_at DESC, id DESC`); `of_cut` e `by_id` intocados |
| Criar | `apps/cli/src/wordcut_cli/render.py` — grupo `render` com `list`, `show`, `download` |
| Alterar | `apps/cli/src/wordcut_cli/__init__.py` — registra `render` |
| Alterar | `apps/cli/src/wordcut_cli/cut.py` — `describe_export` (texto legível da exportação), reusado por `render show` |
| Alterar | `apps/cli/tests/test_cli.py` — `--help` lista o grupo `render` |
| Criar | `packages/core/tests/test_renders_service.py`, `apps/cli/tests/test_render_command.py` |
| Alterar | `packages/core/tests/test_cuts_service.py` — `cut show` com duas exportações, mais antiga primeiro |
| Alterar | `CHANGELOG.md`, `docs/cli.md` §9 |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Ordem | `created_at DESC, id DESC`, em consulta própria (`db.renders.newest_of_cut`); `of_cut` intocado | Mais recente primeiro; `of_cut` alimenta o `cut show`, mais antiga primeiro (docs/cli.md §8.2) — QA D2 |
| Empate de `created_at` | decidido por `id DESC`, com teste | A tarefa grava em segundos — QA L2 |
| `render show` | o `show_render` existente de `service/rendering.py`, sem duplicar | QA D1 |
| Retorno de `render_video` | tipo nomeado `RenderVideo(path, suggested_name)`, no formato de `SermonVideo` | QA D4 |
| Nome legível | `folder_name(service_date da pregação, título do corte) + ".mp4"`, sem `reference` e sem exigir pregação `processed` | Mesma regra do `sermon download`; não reusa `sermon_video` — QA D7, L6 |
| Itens do `render list` | `{"items": [...]}`, cada item no formato de `shown_render` (`id, cut_id, path, duration, created_at, options`); opções como gravadas | QA D8 |
| Caminho | `path` gravado relativo a `WORDCUT_HOME`; `shown_render` (e `show_render`) devolve sempre absoluto, mesmo com `WORDCUT_HOME` relativo, com teste | Igual às mídias da pregação — QA L5 (decisão do orquestrador) |
| `render download` | igual ao `_download` do `sermon`: `copy_without_overwrite(video.path, args.output, video.suggested_name)`, `-o/--output` com padrão `os.curdir`, saída `{"path", "bytes"}`, sem `--json` só o caminho | QA D5 |
| Arquivo ausente | `internal_error` "Arquivo da exportação N não encontrado.", `details: {"render_id": N}`, sem caminho interno | Igual ao item 6 — QA D6 |
| `render show` com arquivo ausente | devolve o registro sem abrir o arquivo; só o `download` dá `internal_error` | QA L4 |
| Proteção do `cut show` | teste de serviço com duas exportações, mais antiga primeiro | QA L1 |
| Trava | nenhuma | Leitura e cópia |
| Documentação | `docs/cli.md` §9 com ordem, formato dos itens e saída `{path, bytes}` do `download` | QA L3 |

---

## Ordem de implementação

- [x] **Passo 1 — Serviço** — listar, detalhar, localizar.
- [x] **Passo 2 — CLI** — `render list/show/download`.
- [x] **Passo 3 — Documentação** — CHANGELOG; docs/cli.md §9 se divergir.

---

## Verificação

- [x] `render list --cut <id> --json` → mais recente primeiro; corte inexistente → `not_found`.
- [x] `render show <id> --json` → campos com `path` absoluto.
- [x] `render download <id>` → nome legível, bytes idênticos, sem sobrescrever; `-o` como no item 6.
- [x] Arquivo ausente → `internal_error` sem caminho; sem trava.
- [x] Quality gates limpos.
