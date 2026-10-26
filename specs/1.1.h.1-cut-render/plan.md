# Plan: Exportar o corte 9:16 (`cut render`)

**Issue**: 1.1.h.1
**Feature**: specs/1.1.h.1-cut-render
**Data**: 2026-10-26

---

## Resumo

`RenderOptions` (validação, padrões, mescla com as salvas) e `estimate`; a timeline e a
montagem recebem as opções de limpeza, pausas e emendas; a codificação recebe resolução,
qualidade, normalização e fades; o tipo de tarefa `render` monta o `EditList` a partir do
corte, roda o pipeline por uma interface (`RenderGateways`, para dublê) e registra a
exportação. A CLI ganha `cut render`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/rendering/options.py` — `RenderOptions` (as oito escolhas gravadas: fillers, stammers, pauses, smooth_joins, fade, normalize, resolution, quality), padrões, `validated(changes)`, `merged(saved, changes)`, `summary(caption)` com as nove escolhas |
| Alterar | `packages/core/src/wordcut/edit/cleanup.py` — `remove_hesitations(words, fillers=True, stammers=True)` |
| Alterar | `packages/core/src/wordcut/edit/timeline.py` — `Cleanup` (fillers, stammers, pausas) e `PAUSES` (`original`, `natural`, `short`); `plan_timeline(..., cleanup=Cleanup())`; `plan_segments(segments, words, fps, energy, cleanup)` recebe as palavras de cada trecho (trecho de uma palavra com `start == end`) |
| Criar | `packages/core/src/wordcut/edit/screen.py` — `caption_words(timeline, respell)`, compartilhado por `short` e pela exportação (`edit/text.py` não pode importar a timeline: ciclo `edit_list` → `text` → `timeline`) |
| Alterar | `packages/core/src/wordcut/edit/assemble.py` — `montage_command(..., smooth_joins=True)` (fade de 15 ms só se ligado) |
| Alterar | `packages/core/src/wordcut/vertical/render.py` — `Encoding` (largura, altura, CRF, normalização, fade) em `render_vertical(..., encoding)`; reenquadramento para a resolução escolhida; fade de 0,5 s no início e no fim quando ligado, limitado à metade da duração |
| Alterar | `packages/core/src/wordcut/cuts/caption.py` — `to_style` escala tamanho, contorno, sombra e `max_width` pela altura do quadro (720/1080 em 720×1280) |
| Criar | `packages/core/src/wordcut/rendering/__init__.py` — porta `RenderGateways` (geometry, energy, assemble, detect, render), `LocalGateways` e `default_gateways()` |
| Criar | `packages/core/src/wordcut/rendering/timeline.py` — `cut_timeline(cut, words, fps, energy, options)` a partir de `cuts.assembly` |
| Criar | `packages/core/src/wordcut/rendering/pipeline.py` — `render_cut(gateways, video, words, cut, caption, options, workdir, output, progress)`, com temporário e `os.replace` |
| Criar | `packages/core/src/wordcut/rendering/estimate.py` — `NOMINAL_FRAME_RATE` e `estimated_duration(cut, words, options)`, sem mídia (energia ausente) |
| Criar | `packages/core/src/wordcut/db/migrations/0009_renders.sql` — tabela `renders` |
| Criar | `packages/core/src/wordcut/db/renders.py` — repositório |
| Alterar | `packages/core/src/wordcut/db/cuts.py` — `set_render_options(connection, cut_id, options, updated_at)` |
| Criar | `packages/core/src/wordcut/tasks/render.py` — tipo `render` em `BUILTIN_KIND_MODULES`; `result.render_id` |
| Alterar | `packages/core/src/wordcut/home.py` — `cut_media(cut_id)` (`media/cuts/<id>/`) |
| Criar | `packages/core/src/wordcut/service/rendering.py` — `start_render(home, cut_id, changes, *, detach, on_progress)`, `estimate_render(connection, cut_id, changes)`, `show_render(connection, home, render_id)` |
| Alterar | `packages/core/src/wordcut/service/cuts.py` — `show_cut(..., home=)`: `render_options` efetivas e `renders` com `path` absoluto |
| Alterar | `apps/cli/src/wordcut_cli/cut.py` — `cut render` com as opções de docs/cli.md §8.7 |
| Alterar | `conftest.py` da raiz — fixture autouse `no_real_rendering` |
| Criar | testes: `test_render_options.py`, `test_cleanup_options.py`, `test_timeline_pauses.py`, `test_render_estimate.py`, `test_render_encoding.py`, `test_render_pipeline.py` (dublês), `test_render_integration.py` (ffmpeg real, clipe lavfi de 2 s, 720×1280, detecção dublê), `test_renders_repository.py`, `test_render_task.py`; `apps/cli/tests/test_cut_render_command.py` |
| Alterar | `packages/core/tests/test_cuts_service.py` — só as duas asserções provisórias de `render_options` |
| Alterar | `docs/adr/0018-...md` e índice, `docs/architecture/README.md` (§4; fluxo da exportação), `README.md`, `CHANGELOG.md`, `docs/cli.md` §8.2, §8.7, §10 e §14, frase do vídeo ausente no spec.md |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Padrões | fillers remove, stammers remove, pauses natural, smooth_joins on, fade on, normalize on, caption = estado do corte, 1080x1920, high | docs/cli.md §8.7 |
| Pausas | `original`: sem encurtar pausas entre palavras do mesmo trecho; `natural`: `PAUSE_S`/`RHETORICAL_PAUSE_S` atuais; `short`: 0,08 s e 0,20 s | Três níveis com o comportamento atual no meio |
| Qualidade | `high` CRF 18; `small` CRF 26 | Atual e um arquivo bem menor |
| Resolução | 1080×1920 ou 720×1280; legendas e câmera escaladas pela largura | Opção do diálogo |
| Fade | 0,5 s de vídeo e áudio no início e no fim (`fade`/`afade` no codificador) | Diálogo "fade no início e no fim" |
| Legenda | `caption` das opções liga/desliga o mesmo campo `enabled` do estilo do corte | FR-006 e docs/cli.md §8.7 |
| Onde fica o arquivo | `WORDCUT_HOME/media/cuts/<cut_id>/<render_id>.mp4`; renderiza em temporário e move no sucesso | Sem arquivo parcial |
| Estimativa | timeline com as opções e as palavras (sem energia de áudio); não salva opções | FR-009; rápida |
| Opções salvas | gravadas no corte ao **iniciar** a exportação (não no `--estimate`) | "As escolhas ficam salvas no corte" |
| Dublês | `RenderGateways` com `default_gateways()` real; fixture autouse que falha se o real for chamado em teste, exceto no teste de integração | Mesmo padrão do item 5 |
| Montagem dos trechos | `cuts.assembly.assemble` dá as palavras de cada trecho pela posição; a timeline recebe essas palavras (trecho de uma palavra com `start == end` incluído). As correções por `word_id` valem só no texto da legenda; limpeza e timeline usam o texto original | Orquestrador, decisão 1; QA, decisão 1 |
| Legenda em 720×1280 | `to_style` escala tamanho, contorno, sombra e `max_width` pela altura do quadro (720/1080) | Orquestrador, decisão 2; QA, decisão 15 |
| `--caption`/`--no-caption` | gravados por `service.cuts.update_caption`; `caption` não entra em `render_options` | Orquestrador, decisão 3; QA, decisão 3 |
| `cut show` | `render_options` efetivas (padrões + salvas, `caption` do corte); `renders` com `path` absoluto; `home` passado como em `show_sermon` (opcional, padrão `Home.from_environment()`, para não mexer nas chamadas existentes) | Orquestrador, decisão 4; QA, decisão 4 |
| Gravação das opções | `db.cuts.set_render_options`, chamado no `admit`, sob a trava; `busy` e `--estimate` não gravam nada | Orquestrador, decisão 5; QA, decisão 2 |
| Taxa da estimativa | `NOMINAL_FRAME_RATE` = 30 quadros/s; a estimativa não abre mídia | Orquestrador, decisão 6; QA, decisão 9 |
| Vídeo ausente | `internal_error`, como `sermon download`; a frase do spec foi corrigida | Orquestrador, decisão 7; QA, decisão 8 |
| `render_id` | `result.render_id` da tarefa; docs/cli.md §10 | Orquestrador, decisão 8; QA, decisão 6 |
| Fixture | `no_real_rendering` autouse no `conftest.py` da raiz; `harmless_tasks` nos testes sem `--wait`; nunca `detached_tasks` com `render` | Orquestrador, decisão 9; QA, decisão 12 |
| Porta | ADR-0018 para `RenderGateways` (geometry, energy, assemble, detect, render), com entrada no índice; README e arquitetura atualizados | Orquestrador, decisão 10 |
| Arquivo sem parcial | o pipeline renderiza na pasta de trabalho e faz `os.replace` só no sucesso; a tarefa grava a linha e move o arquivo para `<render_id>.mp4` na mesma transação; limpeza em `finally`; falha e Ctrl+C usam `internal_error` e `interrupted` | Orquestrador, decisão 11; QA, decisões 7 e 16 |
| Fade curto | duração do fade limitada à metade da duração do corte, sem `st` negativo | Orquestrador, decisão 13; QA, decisão 13 |
| Normalização desligada | sai só o `loudnorm`; o `aresample=48000` fica | Orquestrador, decisão 14; QA, decisão 14 |
| Migração | `0009_renders.sql`, `id` com `AUTOINCREMENT` (o nome do arquivo nunca se repete) e `cut_id` com `ON DELETE CASCADE`, com teste de repositório | Orquestrador |

---

## Ordem de implementação

- [x] **Passo 1 — Opções** — `RenderOptions`, padrões, mescla, resumo, validação.
- [x] **Passo 2 — Limpeza e pausas** — `remove_hesitations` separado; `plan_timeline` com pausas; `estimate`.
- [x] **Passo 3 — Montagem e codificação** — emendas, resolução, qualidade, normalização, fades; integração com ffmpeg real em clipe sintético.
- [x] **Passo 4 — Pipeline do corte** — `render_cut` com correções e estilo da legenda; dublês.
- [x] **Passo 5 — Persistência e tarefa** — migração, repositório, tipo `render`, serviço, `cut show`.
- [x] **Passo 6 — CLI** — `cut render` com opções, `--estimate`, `--wait`.
- [x] **Passo 7 — Documentação** — arquitetura, CHANGELOG, docs/cli.md §8.7 se divergir.

---

## Riscos

- **Tempo de teste**: integração só em 2 s a 720×1280 com detecção dublê.
- **Arquivo órfão (limitação conhecida)**: `sermon suggest` (cortes sugeridos não editados) e o
  reprocessamento apagam cortes; a linha de `renders` sai em cascata, mas o `.mp4` fica em
  `media/cuts/<cut_id>/`. Tratar em 1.2.b (apagar corte e exportações).
- **Desvio do comportamento atual**: com as opções padrão, a timeline deve ser idêntica à do
  `short` atual (teste de regressão).

---

## Verificação

- [x] `cut render <id> --wait --json` (dublês) → exportação registrada com `{id, cut_id, path, duration, created_at, options}`.
- [x] Opções salvas e reutilizadas quando omitidas.
- [x] `--estimate` → duração e resumo, sem tarefa, sem trava, sem salvar.
- [x] Sem `--wait` → tarefa `render`; `task show` traz `render_id`.
- [x] Cada opção altera o que deve (limpeza, pausas, emendas, fade, normalização, legenda, resolução, qualidade), provado por comando gerado ou timeline.
- [x] Integração ffmpeg real (clipe sintético) → arquivo 720×1280 com a duração esperada.
- [x] `busy`, `sermon_not_processed`, `not_found`; falha → sem exportação e sem arquivo parcial.
- [x] Opções padrão → timeline idêntica à do pipeline atual.
- [x] Quality gates limpos.
