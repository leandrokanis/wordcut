# Spec: Sequência da prévia de um corte (`cut preview`)

**Issue**: 1.1.g.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.g-preview-without-render.md §1.1.g.1;
docs/cli.md §8.3; constituição §IV
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A prévia de um corte toca o vídeo 16:9 pulando de trecho em trecho, sem renderizar. Pela CLI,
o agente confere a montagem pela sequência que a prévia tocaria: cada trecho com início e fim
na pregação e o texto, já com as correções de grafia. A mesma sequência alimenta a prévia da
web (fase 3).

---

## Cenários de aceite

**Cenário: sequência da prévia**
- **Dado** um corte com três trechos, um deles fora da ordem da pregação
- **Quando** o operador roda `wordcut cut preview <id> --json`
- **Então** recebe `{"cut_id", "duration", "segments": [{"start", "end", "text",
  "out_of_order"}]}` na ordem de montagem, com tempos da pregação e `out_of_order: true` no
  trecho que volta no tempo

**Cenário: nunca bloqueada**
- **Dado** uma tarefa segurando a trava de processamento
- **Quando** o operador pede a prévia
- **Então** ela sai normalmente

### Casos de borda

- Corte inexistente → `not_found`.
- Texto com correções de grafia aplicadas (quando existirem, item 13).
- Sem `--json`, uma linha por trecho: `[início → fim] texto`, com `↑` nos fora de ordem.

---

## Requisitos funcionais

- **FR-001**: `cut preview <id>` DEVE devolver os trechos na ordem de montagem, com início e fim
  em tempo da pregação, texto e marca de fora de ordem, mais a duração total.
- **FR-002**: A prévia NÃO DEVE tocar vídeo, renderizar nem pegar a trava.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/service/cuts.py` — `preview_cut`.
- `apps/cli/src/wordcut_cli/cut.py` — `preview`.

### Fora de escopo
- Prévia com vídeo no navegador (fase 3).
