# Spec: Ver e escolher cortes sugeridos (`cut list/show/choose/discard/restore`)

**Issue**: 1.1.e.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.e-choose-suggested-scripts.md §1.1.e.1, §1.1.e.2;
docs/cli.md §8.1, §8.2, §8.4; constituição §I
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente vê os cortes que o LLM sugeriu para uma pregação, com o texto montado, a
duração e o estado, e escolhe, descarta ou restaura cada um. Nada disso altera o conteúdo do
corte.

---

## Cenários de aceite

**Cenário: listar cortes da pregação**
- **Dado** uma pregação com cortes sugeridos, escolhidos e descartados
- **Quando** o assistente roda `wordcut cut list --sermon <id> --json`
- **Então** recebe `{"items": [...]}` com id, título, texto montado, duração e estado, com os
  descartados por último; `--status` filtra

**Cenário: detalhar um corte**
- **Dado** um corte
- **Quando** o assistente roda `cut show <id> --json`
- **Então** recebe texto montado, duração, estado, faixa na pregação, `segments` (faixas de
  palavras com tempos e texto), `words` (com `word_id`, texto, tempos e correção),
  `caption` e `render_options` (padrões) e `renders: []`

**Cenário: escolher, descartar, restaurar**
- **Dado** um corte sugerido
- **Quando** o assistente roda `cut choose`, depois `cut discard`, depois `cut restore`
- **Então** o estado passa a `chosen`, `discarded` e volta a `suggested`, sem mudar trechos

### Casos de borda

- ID inexistente → `not_found`.
- Pregação inexistente no `list` → `not_found`.
- Repetir a mesma transição é idempotente (saída 0).
- `restore` de um corte que não está descartado → idempotente, devolve o corte.

---

## Requisitos funcionais

- **FR-001**: `cut list --sermon <id> [--status]` DEVE listar com texto montado, duração e
  estado, descartados por último.
- **FR-002**: `cut show <id>` DEVE devolver o corte completo conforme docs/cli.md §8.2.
- **FR-003**: `choose`, `discard` e `restore` DEVEM mudar só o estado.
- **FR-004**: Texto montado DEVE ser a concatenação dos trechos na ordem; duração, a soma das
  faixas (sem limpeza).

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/service/cuts.py` — serviço de cortes.
- `apps/cli/src/wordcut_cli/cut.py` — grupo `cut`.

### Fora de escopo
- Prévia, grafia, legenda, exportação (itens 12–15) e edição de conteúdo (onda 6).

---

## Pressupostos

- A tabela de cortes vem do item 9; `caption` e `render_options` nulos no banco significam os
  padrões (definidos nos itens 14 e 15; aqui, objetos vazios).
