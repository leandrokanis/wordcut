# ADR-0001: Registrar decisões de arquitetura em ADRs

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

As decisões de arquitetura estavam espalhadas entre a constituição, os requisitos e a
conversa. Quem chega ao projeto, pessoa ou agente, não sabe por que algo é como é.

## Decisão

Cada decisão de arquitetura vira um arquivo em `docs/adr/`, numerado (`NNNN-titulo.md`),
no formato de Michael Nygard: contexto, decisão e consequências. O índice fica em
`docs/adr/README.md`. ADR aceita não é editada: uma decisão nova a substitui, e as duas
apontam uma para a outra.

## Consequências

- A constituição guarda princípios; as ADRs guardam o porquê de cada escolha técnica.
- Mudança de arquitetura exige ADR e atualização de `docs/architecture/` no mesmo commit.
