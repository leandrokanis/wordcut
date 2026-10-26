# Plan: Monorepo com workspace e Docker Compose

**Issue**: monorepo
**Feature**: specs/monorepo-workspace-docker
**Data**: 2026-10-26

---

## Resumo

Move o domínio para `packages/core` (pacote `wordcut`), a CLI atual para `apps/cli`
(pacote `wordcut_cli`), cria `apps/api` (FastAPI com `/api/health`) e `apps/web` (Vite +
React + TS com página que consulta a API), une os projetos Python num workspace `uv` com
raiz virtual e orquestra tudo com `compose.yaml`. Comportamento da CLI inalterado.

Decisões tomadas pela recomendação do agente, em execução automatizada aprovada pelo
administrador (specs/roadmap.md).

---

## Componentes em escopo

- `packages/core` — domínio atual, sem a CLI.
- `apps/cli` — CLI atual.
- `apps/api` — esqueleto novo.
- `apps/web` — esqueleto novo.
- Raiz — workspace, lock, Compose, Docker, documentação.

---

## Contexto de código

| Situação | Path |
|---|---|
| Mover | `src/wordcut/**` (exceto `cli.py`) → `packages/core/src/wordcut/**` (com `git mv`, preservando histórico) |
| Mover | `src/wordcut/cli.py` → `apps/cli/src/wordcut_cli/__init__.py` (`main` e `build_parser` iguais) |
| Mover | `tests/*.py` → `packages/core/tests/` (todos testam domínio) |
| Criar | `packages/core/pyproject.toml` — projeto `wordcut-core`, dependências atuais, extra `asr` |
| Criar | `apps/cli/pyproject.toml` — projeto `wordcut-cli`, depende de `wordcut-core`, script `wordcut = "wordcut_cli:main"` |
| Criar | `apps/cli/tests/test_cli.py` — `--help` lista os comandos atuais |
| Criar | `apps/api/pyproject.toml` — projeto `wordcut-api`, depende de `wordcut-core`, `fastapi`, `uvicorn[standard]` |
| Criar | `apps/api/src/wordcut_api/__init__.py`, `apps/api/src/wordcut_api/app.py` — `create_app()` e rota `GET /api/health` |
| Criar | `apps/api/tests/test_health.py` — via `fastapi.testclient.TestClient` |
| Alterar | `pyproject.toml` — raiz virtual: `[tool.uv.workspace]`, `[tool.uv.sources]`, grupo `dev` (pytest, ruff, mypy, stubs, httpx), configs de ruff, mypy (`files` dos três `src`) e pytest (`testpaths` dos três `tests`, `--import-mode=importlib`) |
| Alterar | `uv.lock` — regenerado |
| Criar | `apps/web/` — `package.json`, `package-lock.json`, `index.html`, `vite.config.ts` (proxy `/api` → `http://127.0.0.1:8781` em dev), `tsconfig*.json`, `eslint.config.js`, `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx`, `src/api.ts` |
| Criar | `docker/python/Dockerfile` — base `python:3.12-slim-bookworm` + ffmpeg + `uv`; alvos `api` e `cli`; `ARG WITH_ASR=0` |
| Criar | `apps/web/Dockerfile` — build no `node:22-alpine`, serve no `nginx:1.27-alpine` |
| Criar | `apps/web/nginx.conf` — SPA com `try_files` e `location /api/` → `http://api:8000` com `proxy_buffering off` |
| Criar | `compose.yaml` — `name: wordcut`; serviços `api`, `web`, `cli` (perfil `tools`) |
| Criar | `.dockerignore` — `.git`, `.venv`, `node_modules`, `dist`, caches, `*.mp4`, `*.wav`, `*cookies*` |
| Alterar | `.gitignore` — `node_modules/`, `apps/web/dist/` |
| Alterar | `README.md`, `CONTRIBUTING.md` (§3.2 comandos), `docs/architecture/README.md` (§4 estado), `skills/*/SKILL.md` se citarem caminhos de `src/` |

---

## Comandos de verificação

| Componente | Um arquivo de teste | Suíte | Checagem estática |
|---|---|---|---|
| Python (core, cli, api) | `uv run pytest <arquivo> -q` | `uv run pytest -q` | `uv run ruff check . && uv run ruff format --check . && uv run mypy` |
| `apps/web` | `npm --prefix apps/web test -- <arquivo>` | `npm --prefix apps/web test` | `npm --prefix apps/web run typecheck && npm --prefix apps/web run lint` |
| Docker | — | `docker compose config -q && docker compose build api web cli` | — |

Pré-requisitos: `uv sync --all-packages` na raiz; `npm --prefix apps/web ci`.
Verificação ponta a ponta: `docker compose up -d api web`, `curl -fsS
http://127.0.0.1:8780/api/health`, `docker compose down`. Não tocar em outras stacks Docker
da máquina.

---

## Decisões técnicas

| Decisão | Escolha | Justificativa |
|---|---|---|
| Raiz do workspace | virtual (sem `[project]`), membros `packages/core`, `apps/cli`, `apps/api` | A raiz não é uma aplicação (ADR-0002) |
| Nome de import do core | continua `wordcut` | Evita reescrever imports do domínio e dos testes |
| Nomes de distribuição | `wordcut-core`, `wordcut-cli`, `wordcut-api` | Um nome por projeto, sem colisão com o import |
| Configuração de ferramentas | `ruff`, `mypy` e `pytest` só na raiz | Um comando da raiz cobre todos (CONTRIBUTING §3.2) |
| Testes com nomes iguais em projetos diferentes | `--import-mode=importlib` | Sem `__init__.py` em `tests/` nem colisão de módulo |
| API | fábrica `create_app()`; `uvicorn wordcut_api.app:create_app --factory` | Testável sem estado global |
| Web | Vite + React + TS, Vitest + Testing Library, ESLint flat config, `tsc -b` | Padrão do ecossistema; ADR-0008 |
| Imagem Python | um `Dockerfile` multi-stage com alvos `api` e `cli` | API e CLI compartilham o ambiente (ADR-0003) sem duplicar receita |
| WhisperX na imagem | `ARG WITH_ASR=0` por padrão | Imagem CUDA tem vários GB; o item 5 liga |
| GPU no Compose | nenhuma reserva agora; virá num `compose.gpu.yaml` no item 5 | Sem o NVIDIA Container Toolkit, a reserva quebra o `up` |
| Dados | bind mount `${WORDCUT_DATA:-${HOME}/.local/share/wordcut}` → `/data`, `WORDCUT_HOME=/data` | CLI no host e contêineres veem o mesmo estado (ADR-0003, ADR-0006) |
| Segredos | bind mount `${HOME}/.config/wordcut` → `/config:ro`, `WORDCUT_CONFIG=/config` | Só leitura; nunca na imagem |
| Usuário nos contêineres | `user: "${UID:-1000}:${GID:-1000}"` | Arquivos no volume continuam do usuário do host; segredos `600` legíveis |
| Portas | `web` em `127.0.0.1:${WORDCUT_WEB_PORT:-8780}`; `api` em `127.0.0.1:${WORDCUT_API_PORT:-8781}` | Só localhost (§VI); portas livres na máquina |
| Nome do projeto Compose | `name: wordcut` | Não colide com outras stacks da máquina |
| `cli` no Compose | perfil `tools`, `entrypoint: ["wordcut"]` | `docker compose run --rm cli <comando>` sem subir com `up` |

---

## Ordem de implementação

- [x] **Passo 1 — Workspace e core** — mover o domínio e os testes com `git mv`, criar
  `packages/core/pyproject.toml`, raiz virtual com configs de ferramentas, `uv lock`; testes
  do domínio passando da raiz.
- [x] **Passo 2 — CLI** — mover a CLI para `apps/cli` com o script `wordcut`; teste de
  `--help` com os comandos atuais; `uv run wordcut overview` funcionando.
- [x] **Passo 3 — API** — `apps/api` com `create_app()` e `GET /api/health`; teste.
- [x] **Passo 4 — Web** — `apps/web` com página que consulta `/api/health` e mostra o estado;
  teste de componente com `fetch` dublê; typecheck, lint e build.
- [x] **Passo 5 — Docker** — `docker/python/Dockerfile`, `apps/web/Dockerfile`,
  `nginx.conf`, `compose.yaml`, `.dockerignore`; `config`, `build` e verificação ponta a
  ponta.
- [x] **Passo 6 — Documentação** — README (estrutura, como rodar com `uv` e Compose),
  CONTRIBUTING §3.2, `docs/architecture/README.md` §4, CHANGELOG.

---

## Riscos

- **Caminhos relativos ao pacote** (`assets/fonts`, `asr/local.py`, `asr/remote.py`): os
  testes de legenda e de ASR cobrem; conferir que continuam passando.
- **Raiz virtual e grupos de dependência**: se o `uv` não instalar o grupo `dev` na raiz
  virtual, usar `uv sync --all-packages --group dev`, registrado no README.
- **Build da web sem rede no contêiner**: o `npm ci` precisa de rede durante o build; a
  máquina tem.

---

## Fora de escopo

- Contrato novo da CLI, camada de serviço, banco e trava (item 1).
- GPU nos contêineres e WhisperX na imagem (item 5).
- Interface real (fase 3).

---

## Verificação

- [x] `uv sync --all-packages` na raiz instala os três projetos Python.
- [x] `uv run pytest -q` roda os testes de `packages/core`, `apps/cli` e `apps/api` e passa.
- [x] `uv run ruff check .`, `uv run ruff format --check .` e `uv run mypy` limpos.
- [x] `uv run wordcut --help` lista `info`, `transcribe`, `transcribe-live`, `overview`, `cut`,
  `preview`, `short`.
- [x] `npm --prefix apps/web test`, `typecheck`, `lint` e `run build` passam.
- [x] `docker compose config -q` sem erro; `docker compose build api web cli` constrói.
- [x] `docker compose up -d api web` → `curl -fsS http://127.0.0.1:8780/api/health` devolve
  `{"status":"ok"}` e a página inicial responde 200; `docker compose down` em seguida.
- [x] `docker compose run --rm cli --help` mostra a ajuda.
- [x] Portas publicadas só em `127.0.0.1` (`docker compose config` mostra `host_ip: 127.0.0.1`).
- [x] Nenhum segredo copiado para imagem (`.dockerignore` cobre `*cookies*`; nada de
  `~/.config` no contexto).
- [x] README, CONTRIBUTING e `docs/architecture/` atualizados.
