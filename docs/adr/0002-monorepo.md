# ADR-0002: Monorepo com um projeto por aplicação

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

O Wordcut tem quatro peças com ciclos e ferramentas diferentes: o domínio (cortes, legenda,
renderização), a CLI, a API HTTP e a interface web. Num pacote único, a regra de negócio
tende a vazar para a CLI ou para a API, o que contraria o princípio II.

## Decisão

Um repositório com projetos separados:

| Projeto | Linguagem | Pacote |
|---|---|---|
| `packages/core` | Python | `wordcut` (domínio e camada de serviço) |
| `apps/cli` | Python | `wordcut_cli`, executável `wordcut` |
| `apps/api` | Python (FastAPI) | `wordcut_api` |
| `apps/web` | TypeScript (React + Vite) | — |

Os projetos Python formam um workspace do `uv` com um `uv.lock` único na raiz. A web tem o
próprio `package.json`. As apps dependem do `core`; o `core` não depende de app; uma app
não depende de outra.

## Consequências

- A fronteira entre regra de negócio e interface fica explícita e verificável.
- Cada app tem os próprios testes e a própria imagem Docker.
- Ferramentas de qualidade (`ruff`, `mypy`, `pytest`) rodam da raiz sobre todos os projetos
  Python.
