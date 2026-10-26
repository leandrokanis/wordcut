# ADR-0007: Tarefas em processo destacado

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

Tarefas pesadas rodam no processo que as dispara (constituição), mas a CLI também precisa
voltar na hora e permitir esperar depois (`--wait`, `task wait`).

## Decisão

Sem `--wait`, a CLI lança um processo filho em sessão própria, que adquire a trava e roda
a tarefa; o comando devolve o ID da tarefa. Com `--wait`, a tarefa roda em primeiro plano.
O estado da tarefa fica no SQLite; tarefa `running` sem processo vivo vira `failed`.

## Consequências

- A CLI não depende do servidor (princípio II).
- Não há fila nem broker (princípio V).
