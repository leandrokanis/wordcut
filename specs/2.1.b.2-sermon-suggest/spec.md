# Spec: Pedir nova sugestão de cortes (`sermon suggest`)

**Issue**: 2.1.b.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/2.1.b-llm-script-suggestion.md §2.1.b.2, §2.1.b.3;
docs/cli.md §7.6; constituição §III
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O administrador pede uma nova sugestão de cortes para uma pregação já processada, com o
preset padrão ou outro. A chamada é uma tarefa sem a trava de processamento (não usa GPU).
Os cortes sugeridos e não editados são substituídos; os escolhidos, descartados e editados
ficam.

---

## Cenários de aceite

**Cenário: nova sugestão com outro preset**
- **Dado** uma pregação processada com cortes sugeridos, um escolhido e um descartado
- **Quando** o administrador roda `wordcut sermon suggest <id> --preset <p> --wait --json`
- **Então** o LLM é chamado com o prompt do preset `p`, os sugeridos antigos não editados
  são substituídos pelos novos, o escolhido e o descartado permanecem, e o resultado lista os
  cortes novos

**Cenário: sem `--wait`**
- **Dado** uma pregação processada
- **Quando** o administrador roda `sermon suggest <id>`
- **Então** recebe a tarefa `suggest` `running` na hora

**Cenário: máquina ocupada não impede**
- **Dado** outra tarefa segurando a trava de processamento
- **Quando** o administrador pede nova sugestão
- **Então** a tarefa `suggest` roda normalmente

**Cenário: pregação não processada**
- **Dado** uma pregação que não está `processed`
- **Quando** o administrador pede nova sugestão
- **Então** falha com `sermon_not_processed` (saída 5), sem criar tarefa

### Casos de borda

- Preset inexistente → `not_found`.
- LLM falha duas vezes → tarefa `failed` com `llm_error`; cortes antigos intactos.
- Sem modelo ou chave → `llm_not_configured`; nada muda.
- Duas sugestões simultâneas da mesma pregação → a segunda falha com `busy` (por pregação).

---

## Requisitos funcionais

- **FR-001**: `sermon suggest <id> [--preset <id>] [--wait]` DEVE criar uma tarefa `suggest`
  sem a trava global.
- **FR-002**: A tarefa DEVE usar o preset indicado ou o padrão.
- **FR-003**: Os cortes `suggested` não editados DEVEM ser substituídos só se a nova
  sugestão tiver sucesso; escolhidos, descartados e editados DEVEM permanecer.
- **FR-004**: O `--help` DEVE dizer que o comando é do administrador.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — tipo de tarefa `suggest`, substituição dos sugeridos.
- `apps/cli/src/wordcut_cli/sermon.py` — `suggest`.

### Fora de escopo
- Permissões por papel (fase 2: na máquina, a CLI age como administrador).

---

## Pressupostos

- A orquestração de `suggest` (item 9) é reaproveitada sem mudança de esquema.
