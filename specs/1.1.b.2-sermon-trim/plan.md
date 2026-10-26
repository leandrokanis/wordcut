# Plan: Delimitar a pregação pela CLI (`sermon trim`)

**Issue**: 1.1.b.2
**Feature**: specs/1.1.b.2-sermon-trim
**Data**: 2026-10-26

---

## Resumo

Acrescenta ao serviço de pregações a gravação das bordas (`trim_sermon`), com as regras de
faixa mínima, limites e transição de estado, e expõe `sermon trim` e `--start/--end` no
`sermon create`. Reaproveita `parse_timestamp` e o repositório do item 2.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core/src/wordcut/` — serviço e repositório de pregações, tempo.
- `apps/cli/src/wordcut_cli/sermon.py` — `trim` e opções do `create`.
- `packages/core/tests/`, `apps/cli/tests/`.

---

## Contexto de código

| Situação | Path |
|---|---|
| Alterar | `packages/core/src/wordcut/service/sermons.py` — `trim_sermon(conn, sermon_id, start, end) -> dict` e `create_sermon(..., start=None, end=None)` |
| Alterar | `packages/core/src/wordcut/db/sermons.py` — `update_range(sermon_id, live_start, live_end, status)` |
| Alterar | `packages/core/src/wordcut/timefmt.py` — `parse_timestamp` aceita segundos (`754.2`) se ainda não aceitar; erro de formato vira `ValueError` com mensagem clara |
| Alterar | `apps/cli/src/wordcut_cli/sermon.py` — `sermon trim <id> --start T --end T`; `--start/--end` no `create`; aviso de reprocessar via `ctx.warn` |
| Criar | `packages/core/tests/test_sermon_trim.py`, `apps/cli/tests/test_sermon_trim_command.py` |
| Alterar | `CHANGELOG.md` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Faixa mínima | constante `MIN_SERMON_SECONDS = 60` no serviço | 1.1.b (pregação com no mínimo 1 minuto) |
| Transição de estado | `created`/`trimmed`/`failed` → `trimmed`; `processed` mantém o estado; `processing` → `busy` (saída 4, com a tarefa nos `details` quando existir) | 1.1.b.3; não mexer em bordas durante o processamento |
| Aviso de reprocessar | serviço devolve `needs_reprocess: true` quando a pregação é `processed`; a CLI avisa no stderr | Regra no core, apresentação na CLI |
| Validação de tempo | a CLI converte texto em segundos com `parse_timestamp` (`argparse type`); erro → `invalid_argument` com `details.argument` | Erro de formato é erro de uso |
| Regras de faixa | serviço: `0 ≤ start < end ≤ live_duration`, senão `invalid_argument` com `details` (`start`, `end`, `live_duration`) | Regra no core (ADR-0004) |
| `create` com bordas | `--start` e `--end` juntos; só um → `invalid_argument`; cria e chama `trim_sermon` na mesma transação | Não deixa pregação criada sem as bordas pedidas |
| Precisão | segundos `float` arredondados a milissegundos | `HH:MM:SS.mmm` |
| L1 — `duration` | `round(live_end - live_start, 3)` quando há bordas, em `list` e `show`; `null` sem bordas | Cenário 1 exige `duration 2780.0` (orquestrador, rodada 1) |
| L2 — `create` atômico | `create` com bordas valida as bordas contra a duração da live **antes** do insert; `create` inválido não deixa pregação no banco | `insert` faz commit próprio; validar antes evita pregação órfã (orquestrador) |
| L3 — vídeo existente com bordas | `create` aplica `trim_sermon` à pregação existente (mesmas regras e aviso) e devolve `created: false` | Nunca ignorar as bordas em silêncio (orquestrador) |
| L4 — parser estrito | `parse_timestamp` rejeita não finitos, componentes negativos e minutos/segundos ≥ 60 depois do primeiro componente | `inf` gera JSON inválido; `nan` fura comparações (orquestrador) |
| L5 — `live_duration` nula | valida só `0 ≤ start < end` e o mínimo de 60 s; `details.live_duration: null` nos erros | Live ainda no ar (orquestrador) |
| L6 — `busy` sem tarefa | estado `processing` posto por SQL no teste; `details` ausente até existir tarefa (3.1.a.2) | Sem tabela de tarefas (orquestrador) |
| L7 — ordem das validações | `not_found` → `busy` → `invalid_argument` → `sermon_too_short` | Erro mais grave primeiro (orquestrador) |
| L8 — arredondar antes de validar | bordas arredondadas a ms na entrada; a faixa mínima compara a duração arredondada a ms | `1:00.0004` vale 60,000 s (orquestrador) |
| L9 — `updated_at` | `update_range(connection, sermon_id, live_start, live_end, status, updated_at)`; o serviço injeta o relógio (`now`) | Relógio é fronteira (orquestrador) |
| L10 — texto do `trim` | reaproveita o render do `show` | Mesmo formato de `show` (FR-006; orquestrador) |
| L11 — `needs_reprocess` | o serviço devolve o sinal; a CLI o retira antes de imprimir e o usa só para o aviso | `trim --json` igual a `show --json` (orquestrador) |
| Bordas sozinhas no `create` | a CLI recusa com `details.argument` = a opção que falta (`--start`/`--end`); o serviço também recusa (`start`/`end`) | Erro de uso na CLI; regra protegida no core para outros adaptadores |

---

## Ordem de implementação

- [x] **Passo 1 — Regras no serviço** — `trim_sermon` com faixa mínima, limites, transições e
  `needs_reprocess`; repositório `update_range`.
- [x] **Passo 2 — `sermon trim` na CLI** — comando, parser de tempo, aviso, texto e JSON.
- [x] **Passo 3 — `create` com bordas** — `--start/--end` no serviço e na CLI, na mesma
  transação.
- [x] **Passo 4 — Documentação** — CHANGELOG; docs/cli.md só se algo do contrato mudar.

---

## Fora de escopo

- Encostar a borda na palavra mais próxima (questão aberta da 1.1.b).
- `--process` no `create` (item 5).

---

## Verificação

- [x] `sermon trim <id> --start 1:02:10 --end 1:48:30 --json` numa pregação `created` de 2 h →
  `trimmed`, `live_start 3730.0`, `live_end 6510.0`, `duration 2780.0`, saída 0.
- [x] `sermon create <link> --start … --end …` → pregação criada já `trimmed`.
- [x] Faixa < 60 s → `sermon_too_short` (saída 5), nada muda.
- [x] Pregação `processed` → bordas gravadas, estado mantido, aviso no stderr.
- [x] Formato inválido, início ≥ fim, borda fora da live, só uma borda no `create` →
  `invalid_argument`.
- [x] ID inexistente → `not_found`.
- [x] Quality gates limpos.
