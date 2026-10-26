# Plan: Ver e escolher cortes sugeridos

**Issue**: 1.1.e.1
**Feature**: specs/1.1.e.1-cut-choose
**Data**: 2026-10-26

---

## Resumo

Serviço de cortes no core (listar, detalhar, mudar estado) sobre o repositório do item 9, e o
grupo `cut` na CLI com `list`, `show`, `choose`, `discard` e `restore`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/service/cuts.py` — `list_cuts(conn, sermon_id, status)`, `show_cut(conn, cut_id)`, `choose_cut`/`discard_cut`/`restore_cut(conn, cut_id, now)` |
| Alterar | `packages/core/src/wordcut/db/cuts.py` — criar só `by_id` e `set_status` (com `updated_at`); `of_sermon` já existe e mantém a ordem por `id`, de que o `sermon show` depende (D1) |
| Criar | `packages/core/src/wordcut/cuts/assembly.py` — trechos resolvidos por `position` sobre `transcripts.words_of` (D5), texto montado e duração |
| Reusar | `packages/core/src/wordcut/service/sermons.py` — `shown_cut(row)` é o núcleo de cada corte em `list` e `show` (D2) |
| Criar | `apps/cli/src/wordcut_cli/cut.py` — grupo `cut` |
| Alterar | `apps/cli/src/wordcut_cli/legacy.py` — o comando antigo `cut` vira `cut-sermon` (L1) |
| Alterar | `apps/cli/src/wordcut_cli/__init__.py` — registra `cut` |
| Criar | `packages/core/tests/test_cuts_service.py`, `apps/cli/tests/test_cut_command.py`; alterar `apps/cli/tests/test_legacy_commands.py` (`cut-sermon`) |
| Alterar | `CHANGELOG.md`, `docs/architecture/README.md` §4, `README.md`, `skills/video-cortar-pregacao/SKILL.md` (L1) |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Ordem do `list` | `suggested` e `chosen` por `id`, depois `discarded` por `id` | Descartados por último (1.1.e) |
| Texto montado | palavras de cada trecho em ordem (`from_word` a `to_word`, inclusivos, por `position`), trechos unidos com espaço; sem correções neste item: `words[].corrected` = `null` (`str \| None`, o texto corrigido, preenchido pelo item 13) (D3, D5) | Mesmo texto da prévia; não há armazenamento de correções no baseline |
| Duração | soma de `end − start` de cada trecho (primeira palavra ao fim da última), sem ×0,82, arredondada ao ms (D7) | Sem limpeza; a exportação estima a limpeza |
| Transições | qualquer estado → `chosen`/`discarded`; `restore` → `suggested` só a partir de `discarded`, nos outros estados idempotente (L2); repetição idempotente | 1.1.e; spec, casos de borda; docs/cli.md §8.4 |
| Conteúdo intocado | os comandos só escrevem `status` e `updated_at` (teste compara trechos antes e depois) | §I |
| Formato do `show` | `shown_cut(row)` + `sermon_id`, `text`, `duration`; `segments` enriquecidos `[{from_word, to_word, start, end, text}]`, `words: [{word_id, text, start, end, corrected}]`, `caption: row.caption or {}`, `render_options: row.render_options or {}`, `renders: []` (D2, D4) | docs/cli.md §7.2, §8.2; nulo = padrões |
| Item do `list` | `shown_cut(row)` + `sermon_id`, `text`, `duration`, sem `words` (L6) | §8.1 |
| Ordem no repositório | `of_sermon` continua por `id`; "descartados por último" é regra do serviço (D1) | `sermon show` depende da ordem por `id` (§7.2) |
| Comando `cut` da CLI anterior | renomeado `cut-sermon`, mesmo comportamento e com teste; README, skill `video-cortar-pregacao` e CHANGELOG atualizados; removido só no item 18 (L1) | `add_parser("cut")` repetido derruba o parser no Python 3.11 |
| Leitura não escreve | `cut list` e `cut show` não mudam estado (L3) | §8.2 é leitura |
| Retorno das transições | o mesmo objeto de `cut show` (L4) | Uma forma só para o corte |
| Repetir transição | não escreve nada; `updated_at` intacto (L5) | Idempotência sem efeito |
| `not_found` | `details: {"cut_id": N}` no corte, `{"sermon_id": N}` na pregação (L7) | Como `service.sermons._existing` |
| Palavra do trecho ausente | sem tratamento próprio: a falha cai no `internal_error` do contrato da CLI (mensagem em português, sem traceback); invariante do banco (reprocessar apaga os cortes), sem teste próprio (L8) | Não deveria existir |
| Texto sem `--json` | `list`: uma linha por corte com id, estado em português, duração e título; `show`/transições: título, estado, duração, faixa e texto; erro só no stderr (L9) | docs/cli.md §4.2 |
| Arquivos de teste | `cuts.assembly` e `db.cuts.by_id`/`set_status` testados pelo serviço (L10) | Interface pública |

---

## Ordem de implementação

- [x] **Passo 1 — Montagem** — texto montado e duração.
- [x] **Passo 2 — Serviço** — `list_cuts`, `show_cut`, `choose_cut`/`discard_cut`/`restore_cut`.
- [x] **Passo 3 — CLI** — grupo `cut` com os cinco comandos, texto e JSON.
- [x] **Passo 4 — Documentação** — CHANGELOG, arquitetura §4.

---

## Verificação

- [x] `cut list --sermon <id> --json` → itens com texto, duração e estado; descartados por
  último; `--status` filtra; pregação inexistente → `not_found`.
- [x] `cut show <id> --json` → formato de §8.2.
- [x] `choose` → `discard` → `restore` mudam só o estado; trechos idênticos.
- [x] Repetir transição é idempotente; ID inexistente → `not_found`.
- [x] Quality gates limpos.
