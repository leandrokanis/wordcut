# ADR-0006: Trava global com `flock`

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

O princípio IV exige um processamento pesado por vez na máquina inteira, recusando o
segundo pedido sem fila, com liberação automática se o processo morrer.

## Decisão

Um arquivo `processing.lock` em `WORDCUT_HOME`, travado com `fcntl.flock` exclusivo e não
bloqueante. O dono grava no próprio arquivo quem é (tipo, recurso, PID, início). Para saber se
está livre, tenta-se uma trava compartilhada não bloqueante; se ela vier, o conteúdo antigo é
ignorado.

## Consequências

- O kernel libera a trava quando o processo morre; não há trava órfã.
- Funciona entre CLI no host e contêineres, desde que o arquivo esteja em disco local
  compartilhado.
