# Spec: Exportar o corte 9:16 (`cut render`)

**Issue**: 1.1.h.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.h-render-vertical-cut.md §1.1.h.1–1.1.h.3;
docs/cli.md §8.7, §9; constituição §IV
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente exporta o corte em 9:16 com as opções da caixa de exportação (limpeza, edição,
áudio, legenda e vídeo). A exportação é uma tarefa pesada, sob a trava, que usa o estado
atual do corte (trechos, correções de grafia, estilo da legenda) e fica registrada no próprio
corte com data, duração e opções. As opções escolhidas ficam salvas no corte.

---

## Cenários de aceite

**Cenário: exportar com as opções padrão**
- **Dado** um corte escolhido de uma pregação processada e a máquina livre
- **Quando** o assistente roda `wordcut cut render <id> --wait --json`
- **Então** o progresso das etapas aparece no stderr, a exportação fica registrada no corte e
  o JSON traz `{id, cut_id, path, duration, created_at, options}`, com saída 0

**Cenário: opções salvas no corte**
- **Dado** uma exportação feita com `--pauses short --no-fade --resolution 720x1280`
- **Quando** o assistente roda `cut render <id>` sem opções
- **Então** a nova exportação usa as mesmas opções

**Cenário: estimativa sem renderizar**
- **Dado** um corte
- **Quando** o assistente roda `cut render <id> --estimate --json`
- **Então** recebe a duração estimada e o resumo das opções, sem tarefa, sem trava e sem
  salvar opções

**Cenário: em segundo plano**
- **Dado** um corte
- **Quando** o assistente roda `cut render <id>` sem `--wait`
- **Então** recebe a tarefa `render` `running`; ao terminar, `task show` traz `render_id`

### Casos de borda

- Máquina ocupada → `busy` (saída 4), sem tarefa.
- Pregação não processada → `sermon_not_processed`. Pregação processada sem o arquivo do
  vídeo → `internal_error`, como `sermon download`.
- `--caption`/`--no-caption` mudam o mesmo estado de `cut caption --on/--off`.
- Falha da renderização → tarefa `failed`, nenhuma exportação registrada, arquivo parcial
  apagado.
- Corte inexistente → `not_found`.

---

## Requisitos funcionais

- **FR-001**: `cut render <id> [opções] [--estimate] [--wait]` DEVE criar uma tarefa `render`
  sob a trava, que gera o vídeo 9:16 do estado atual do corte.
- **FR-002**: As opções DEVEM ser as de docs/cli.md §8.7, com os padrões dali, salvas no corte
  e reutilizadas quando omitidas.
- **FR-003**: Limpeza: hesitações e gaguejos podem ser removidos ou mantidos, separadamente;
  pausas originais, naturais ou curtas.
- **FR-004**: Edição: emendas suavizadas ou não; fade no início e no fim ou não.
- **FR-005**: Áudio normalizado a −14 LUFS ou não.
- **FR-006**: Legenda com o estilo do corte e as correções de grafia, ou sem legenda.
- **FR-007**: Vídeo em 1080×1920 ou 720×1280, qualidade alta ou arquivo menor.
- **FR-008**: Cada exportação DEVE ficar registrada no corte com caminho, duração, data e
  opções; `cut show` lista as exportações.
- **FR-009**: `--estimate` DEVE calcular a duração da timeline limpa sem renderizar.

---

## Entidades e dados

- **Exportação (`render`)**: id, cut_id, path (relativo a `WORDCUT_HOME`), duration, options
  (JSON), created_at.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — opções de exportação, timeline com opções de limpeza e
  pausa, montagem e renderização parametrizadas, tipo de tarefa `render`, migração, serviço.
- `apps/cli/src/wordcut_cli/cut.py` — `render`.

### Fora de escopo
- `render list/show/download` (item 16).
- Exportação pela web (fase 3).

---

## Pressupostos

- O pipeline atual (`short.render_short`: montagem, detecção do pregador, câmera, legendas,
  codificação) é reaproveitado, parametrizado pelas opções.
- Testes usam dublês para detecção e codificação, mais uma integração com `ffmpeg` real num
  clipe sintético curto em baixa resolução; nenhum vídeo real.
