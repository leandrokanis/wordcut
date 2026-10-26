# Spec: Delimitar a pregação pela CLI (`sermon trim`)

**Issue**: 1.1.b.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.b-mark-sermon-range.md §1.1.b.2; docs/cli.md §3.4,
§7.1 (`--start`/`--end`), §7.3
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O agente operador informa, sem tela, onde a pregação começa e termina dentro da live. As
bordas ficam gravadas na pregação, em tempo da live, e liberam o processamento. As mesmas
bordas podem ser passadas já na criação.

---

## Cenários de aceite

**Cenário: delimitar uma pregação criada**
- **Dado** uma pregação `created` de uma live com 2 h
- **Quando** o operador roda `wordcut sermon trim <id> --start 1:02:10 --end 1:48:30 --json`
- **Então** a pregação passa a `trimmed`, com `live_start: 3730.0`, `live_end: 6510.0` e
  `duration: 2780.0`, e a saída é 0

**Cenário: delimitar na criação**
- **Dado** um link novo
- **Quando** o operador roda `sermon create <link> --start 1:02:10 --end 1:48:30`
- **Então** a pregação é criada já `trimmed`, com as bordas

**Cenário: faixa curta demais**
- **Dado** uma pregação criada
- **Quando** o operador delimita uma faixa de menos de 1 minuto
- **Então** o comando falha com `sermon_too_short` (saída 5) e nada muda

**Cenário: pregação já processada**
- **Dado** uma pregação `processed`
- **Quando** o operador muda as bordas
- **Então** as bordas são gravadas, o estado continua `processed`, e um aviso no stderr diz
  que reprocessar exige `sermon process --force`

### Casos de borda

- Formatos aceitos: `HH:MM:SS[.mmm]`, `MM:SS[.mmm]` e segundos (`754.2`); outro formato →
  `invalid_argument` com `details.argument`.
- `--start` maior ou igual a `--end` → `invalid_argument`.
- Borda fora da duração da live → `invalid_argument`.
- `--start` sem `--end` no `create` (ou o contrário) → `invalid_argument`.
- ID inexistente → `not_found`.

---

## Requisitos funcionais

- **FR-001**: `sermon trim <id> --start T --end T` DEVE gravar as bordas em tempo da live e
  levar uma pregação `created` (ou `failed`) para `trimmed`.
- **FR-002**: A faixa DEVE ter pelo menos 60 s; senão, `sermon_too_short`.
- **FR-003**: As bordas DEVEM estar dentro de `[0, duração da live]`, com início antes do fim.
- **FR-004**: `sermon create` DEVE aceitar `--start` e `--end` juntos, com o mesmo efeito do
  `trim`.
- **FR-005**: Numa pregação `processed`, o `trim` DEVE gravar as bordas sem mudar o estado e
  avisar no stderr.
- **FR-006**: A resposta DEVE ser a pregação atualizada, no formato de `sermon show`.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — serviço de pregações (validação e gravação das bordas).
- `apps/cli/src/wordcut_cli/` — `sermon trim` e opções do `sermon create`.
- Testes no core e na CLI.

### Fora de escopo
- Encostar a borda na palavra mais próxima (questão aberta da 1.1.b).
- Processar (`--process`, item 5).

---

## Pressupostos

- O parser de tempo existente (`wordcut.timefmt.parse_timestamp`) é reaproveitado.
