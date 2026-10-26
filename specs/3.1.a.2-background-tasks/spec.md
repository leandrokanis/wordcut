# Spec: Tarefas em segundo plano, `--wait` e `task`

**Issue**: 3.1.a.2 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/3.1.a-processing-lock-and-status.md §3.1.a.2;
docs/cli.md §6, §10; ADR-0006, ADR-0007
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O agente operador dispara operações pesadas e quer duas coisas: voltar na hora com o ID da
tarefa, ou esperar o fim com `--wait`, vendo o progresso no stderr. Também quer consultar e
esperar uma tarefa já lançada. Este item cria o mecanismo de tarefas que `sermon process`,
`sermon suggest` e `cut render` vão usar.

---

## Cenários de aceite

**Cenário: lançar e voltar na hora**
- **Dado** a máquina livre e uma operação pesada de teste
- **Quando** o operador a dispara sem `--wait`
- **Então** recebe `{"task_id", "kind", "status": "running", …}` na hora, e a tarefa segue num
  processo destacado que segura a trava

**Cenário: esperar com `--wait`**
- **Dado** a máquina livre
- **Quando** o operador dispara a operação com `--wait`
- **Então** a tarefa roda em primeiro plano, o progresso vai para o stderr, o stdout traz o
  resultado final e a saída é 0 (ou o código do erro, se falhar)

**Cenário: esperar uma tarefa lançada**
- **Dado** uma tarefa destacada em andamento
- **Quando** o operador roda `wordcut task wait <id>`
- **Então** o comando acompanha o progresso e termina com o resultado e a saída da tarefa

**Cenário: máquina ocupada**
- **Dado** uma tarefa com trava em andamento
- **Quando** outra operação com trava é disparada
- **Então** falha na hora com `busy` (saída 4), sem lançar processo nem criar tarefa

**Cenário: tarefa órfã**
- **Dado** uma tarefa `running` cujo processo morreu
- **Quando** alguém consulta a tarefa ou o `status`
- **Então** ela aparece `failed`, com erro dizendo que foi interrompida

**Cenário: status mostra a tarefa**
- **Dado** uma tarefa em andamento
- **Quando** o operador roda `wordcut status`
- **Então** vê a trava com o ID da tarefa e a lista de tarefas em andamento

### Casos de borda

- Ctrl+C durante `--wait` interrompe a tarefa, marca `failed` e sai com 130.
- Ctrl+C em `task wait` de tarefa destacada só para a espera; a tarefa continua.
- Tarefa sem trava (tipo `suggest`) roda mesmo com a máquina ocupada.
- `task show` de ID inexistente → `not_found`.

---

## Requisitos funcionais

- **FR-001**: Toda tarefa DEVE ter ID, tipo (`process` | `render` | `suggest`), recurso,
  estado (`running` | `succeeded` | `failed`), progresso, início, fim, erro e resultado,
  gravados no SQLite.
- **FR-002**: Sem `--wait`, a tarefa DEVE rodar num processo em sessão própria, que adquire e
  segura a trava (quando o tipo exige) até terminar.
- **FR-003**: A trava DEVE ser verificada antes de criar a tarefa; ocupada → `busy`.
- **FR-004**: Com `--wait`, a tarefa DEVE rodar em primeiro plano com o progresso no stderr.
- **FR-005**: `task list [--status] [--kind]`, `task show <id>` e `task wait <id>` DEVEM
  existir; `task wait` DEVE terminar com a saída da tarefa.
- **FR-006**: Tarefa `running` sem processo vivo DEVE virar `failed` na próxima leitura.
- **FR-007**: `wordcut status` DEVE incluir o ID da tarefa que segura a trava e as tarefas em
  andamento.

---

## Entidades e dados

- **Tarefa (`task`)**: id, kind, resource_type, resource_id, status, progress (0–1),
  progress_message, pid, started_at, finished_at, error (código e mensagem), result (JSON).

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — modelo de tarefa, execução destacada, integração com a trava,
  serviço de tarefas, migração.
- `apps/cli/src/wordcut_cli/` — `--wait`, `task list/show/wait`, `status` ampliado.
- Testes com uma operação de teste rápida (sem YouTube nem GPU).

### Fora de escopo
- As operações reais (`process`, `suggest`, `render`), que chegam nos itens 5, 10 e 15.
- Cancelamento de tarefa.

---

## Pressupostos

- A operação de teste é registrada só nos testes, por um registro de tipos de tarefa que os
  itens seguintes também usam.
