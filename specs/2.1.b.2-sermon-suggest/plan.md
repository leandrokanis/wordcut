# Plan: Pedir nova sugestão de cortes (`sermon suggest`)

**Issue**: 2.1.b.2
**Feature**: specs/2.1.b.2-sermon-suggest
**Data**: 2026-10-26

---

## Resumo

Novo tipo de tarefa `suggest` (`needs_lock=False`) que reaproveita a orquestração do item 9
com o preset escolhido e substitui, numa transação, os sugeridos não editados. Exclusão por
pregação evita duas sugestões simultâneas. A CLI ganha `sermon suggest`.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Contexto de código

| Situação | Path |
|---|---|
| Criar | `packages/core/src/wordcut/tasks/suggest.py` — tipo `suggest` (`needs_lock=False`), em `BUILTIN_KIND_MODULES` de `packages/core/src/wordcut/tasks/__init__.py`; resolve o preset por `show_preset(params["preset_id"])` |
| Criar | `packages/core/src/wordcut/service/suggestion.py` — `start_suggestion(home, sermon_id, preset_id=None, *, detach, on_progress=None)` com pré-condições (pregação, preset, LLM configurado) e exclusão por pregação no `admit` |
| Alterar | `packages/core/src/wordcut/suggestion/__init__.py` — `suggest(connection, sermon_id, preset, *, replace_suggested=False)`; `SuggestionResult` com `cut_ids`; `require_configured(connection)` público (o que era `_configured_model`) |
| Alterar | `packages/core/src/wordcut/db/cuts.py` — `delete_unedited_suggestions(connection, sermon_id)`; `insert_many` devolve os IDs gravados |
| Alterar | `packages/core/src/wordcut/service/sermons.py` — `processed_row` (recusa `not_found`/`sermon_not_processed`, reaproveitada por `sermon_video`) e `shown_cut` públicos |
| Alterar | `apps/cli/src/wordcut_cli/sermon.py` — `sermon suggest <id> [--preset] [--wait]` com renderizador próprio |
| Criar | `packages/core/tests/test_suggest_task.py`, `apps/cli/tests/test_sermon_suggest_command.py`; acréscimos em `packages/core/tests/test_suggestion.py` e `test_cuts_repository.py` |
| Alterar | `CHANGELOG.md`, `docs/cli.md` §5.3 e §7.6, `docs/architecture/README.md` (tabela de módulos) |
| Criar (QA rodada 1) | `packages/core/src/wordcut/network.py` — `refuse_when_forbidden(service)`; chamada por `suggestion.default_model` e `processing.default_gateways` (`packages/core/src/wordcut/processing/__init__.py`); `conftest.py` da raiz com a autouse `no_network`; `packages/core/tests/test_network_guard.py`; `docs/adr/0017-testes-sem-rede-real.md`, `CONTRIBUTING.md` §3, `README.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Trava | `needs_lock=False` | ADR-0010; não usa GPU (docs/cli.md §6.1) |
| Exclusão por pregação | antes de criar a tarefa, se houver tarefa `suggest` `running` da mesma pregação (após reconciliar órfãs) → `busy` | Evita gravação concorrente no caso sequencial (ver Riscos) |
| Substituição | só no sucesso, numa transação | Falha não perde cortes antigos |
| Erros | `sermon_not_processed`, `not_found` (pregação ou preset), `llm_not_configured`, `llm_error` | Contrato existente |
| L1 — assinatura | `suggest(connection, sermon_id, preset, *, replace_suggested: bool = False)`; a tarefa resolve o preset com `show_preset` ou `default_preset`; o `process` não muda | O preset já chega resolvido no baseline (QA L1) |
| L2 — resultado | `{"sermon_id", "preset_id", "suggested_cuts": [cortes no formato de sermon show], "suggestion_warnings": [...]}`; `SuggestionResult` devolve os IDs gravados (`cut_ids`); documentado em §7.6 | O `process` não tem bloco `suggested_cuts`/`discarded` (QA L2) |
| L3 — LLM não configurado | `start_suggestion` confere modelo e chave antes de criar a tarefa (`llm_not_configured`, sem tarefa, sem tocar em `suggestion_error`); a conferência dentro de `suggest` continua como rede | "Nada muda" do spec (QA L3) |
| L4 — corrida da exclusão | risco aceito (Riscos e §7.6); só o caso sequencial é testado | Sem mudança de esquema (QA L4) |
| L5 — dublê e processo destacado | testes sem `--wait` usam `harmless_tasks`; o registro do tipo é provado num interpretador novo | O dublê do LLM não alcança o `runner` destacado (QA L5) |
| L6 — `suggestion_error` | `llm_error` grava `suggestion_error` (ADR-0016) e o sucesso limpa; documentado | Coerência com o `process` (QA L6) |
| L7 — resposta válida sem corte aproveitável | é sucesso: os sugeridos não editados saem, `suggested_cuts: []`, avisos presentes; documentado e testado | "Só no sucesso" + contrato atual (QA L7) |
| L8 — `busy` por pregação | `details` com `task_id`, `kind` e `started_at` da sugestão em andamento; §5.3 e §7.6 atualizados; sem ADR nova | Mesmo formato do `busy` da trava (QA L8) |
| L9 — reprocessamento durante a sugestão | na transação de substituição, conferir que a pregação segue `processed` com o mesmo `processed_at` do início; se não, `sermon_not_processed` sem gravar nada (nem `suggestion_error`) | Os IDs de palavra dos cortes não têm FK (QA L9) |
| L10 — progresso e saída legível | etapa `sugerindo`; renderizador legível próprio para a tarefa lançada e para o resultado | QA L10 |
| L11 — preset na tarefa | `params` guardam o `preset_id` resolvido; preset apagado antes da execução → tarefa `failed` com `not_found` | `task show` diz qual preset valeu (QA L11) |
| Guarda global contra rede (decisão do orquestrador, QA rodada 1) | `conftest.py` da raiz: autouse `no_network` define `WORDCUT_FORBID_NETWORK`; `suggestion.default_model` e `processing.default_gateways` recusam com `network_error` (`details.forbidden_by`) por `wordcut.network.refuse_when_forbidden`; um `runner` destacado real de `suggest` com chave fictícia termina `failed` com esse erro e sem processo vivo; as autouse `no_real_task_process` locais saem | O dublê não alcança o processo destacado; um runner real chamou o OpenRouter (ADR-0017) |

## Riscos

- **Corrida da exclusão por pregação (L4)**: sem trava (`needs_lock=False`), o `admit` confere
  e `_create` grava em outra conexão; duas chamadas simultâneas podem passar as duas. Aceito:
  a segunda substituição só troca os sugeridos não editados de novo, numa transação.

---

## Ordem de implementação

- [x] **Passo 1 — Substituição no core** — `replace_suggested` e repositório.
- [x] **Passo 2 — Tipo de tarefa e serviço** — `suggest` sem trava, exclusão por pregação, pré-condições.
- [x] **Passo 3 — CLI** — `sermon suggest` com `--preset` e `--wait`.
- [x] **Passo 4 — Documentação** — CHANGELOG; docs/cli.md §7.6 se divergir.

---

## Verificação

- [x] Com `--wait` e dublê de LLM: sugeridos não editados substituídos; escolhido e descartado intactos.
- [x] Sem `--wait` → tarefa `suggest` `running`.
- [x] Com `lock_owner` segurando a trava → `suggest` roda.
- [x] Pregação não processada → `sermon_not_processed`; preset inexistente → `not_found`.
- [x] LLM falha → `llm_error`, cortes antigos intactos.
- [x] Segunda sugestão simultânea da mesma pregação → `busy`.
- [x] Quality gates limpos.
