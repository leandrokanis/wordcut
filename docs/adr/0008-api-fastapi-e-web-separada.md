# ADR-0008: API FastAPI e web em contêiner próprio

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

A interface é uma SPA em React. A constituição previa o FastAPI servindo a interface
compilada; com o monorepo (ADR-0002) e o Compose (ADR-0003), a interface é um projeto à
parte.

## Decisão

A API é FastAPI em `apps/api`, com o progresso das tarefas por Server-Sent Events. A web é
compilada pelo Vite e servida por um contêiner estático próprio, que repassa `/api` para a
API, de modo que o navegador vê uma origem só.

## Consequências

- Sem CORS: a interface e a API respondem na mesma origem.
- Substitui a cláusula "o FastAPI serve a interface compilada" da constituição 2.x (emenda
  3.0.0).
