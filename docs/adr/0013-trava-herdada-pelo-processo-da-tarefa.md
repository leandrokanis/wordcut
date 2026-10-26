# ADR-0013: Trava herdada pelo processo da tarefa

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0007](0007-tarefas-em-processo-destacado.md), que continua valendo: a
tarefa sem `--wait` roda num processo destacado, com o estado no SQLite. Esta ADR muda só
quem adquire a trava ([ADR-0006](0006-trava-global-flock.md)) e em que ordem.

## Contexto

A ADR-0007 diz que o processo destacado adquire a trava. Assim, haveria uma janela entre o
comando lançar o filho e o filho travar: dois lançamentos ao mesmo tempo voltariam os dois
com `task_id`, e um deles falharia depois, já em segundo plano. Mas [docs/cli.md](../cli.md)
§6.4 exige `busy` na hora, sem criar tarefa e sem lançar processo. Além disso, quem encadeia
`wordcut task wait 9 && <outra operação>` não pode receber `busy` porque a tarefa 9 gravou o
fim antes de soltar a trava.

## Decisão

- Quem lança a tarefa adquire a trava (`flock` exclusivo, não bloqueante) **antes** de criar
  a tarefa. Ocupada → `busy`, sem tarefa e sem processo. Os `details` do `busy` trazem o
  `task_id` do dono.
- Com a trava, cria a tarefa `running` com o próprio PID e o nome do host, grava o `task_id`
  na descrição do dono e lança o filho em sessão própria, com o descritor da trava herdado
  (`pass_fds`). Em seguida, fecha a própria cópia do descritor e grava na tarefa o PID do
  filho.
- O filho (`python -m wordcut.tasks.runner <task_id> <descritor>`) reescreve o dono da trava
  com o próprio PID e roda a tarefa. Ao terminar, **solta a trava e só depois grava o estado
  final**. Em primeiro plano (`--wait`), a ordem é a mesma.
- Quem espera (`task wait`, `--wait`) só termina no estado final; por isso, encontra a trava
  livre.
- Tarefa `running` é órfã quando, no mesmo host, o processo dela não existe mais ou é zumbi;
  na leitura, vira `failed` com o código `interrupted`. A tarefa dona da trava está viva, e
  a tarefa de outro host (outro contêiner, outro espaço de PIDs) não é julgada pelo PID.
- Tipo de tarefa sem trava (`suggest`) não toca na trava e roda com a máquina ocupada.

## Consequências

- `busy` é decidido antes de existir tarefa ou processo; não há janela entre checar e travar.
- A trava vive exatamente enquanto vive o processo da tarefa; se ele morrer, o kernel a
  solta (ADR-0006).
- `task wait 9 && <outra operação com trava>` não recebe `busy` espúrio.
- Um PID reaproveitado pode fazer uma tarefa órfã parecer viva; aceito no MVP.
- Uma tarefa de outro host cujo processo morreu sem gravar o fim fica `running` para quem lê
  de fora daquele host.
