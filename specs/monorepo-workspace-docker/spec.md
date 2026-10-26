# Spec: Monorepo com workspace e Docker Compose

**Issue**: monorepo (sem rastreador; item 0 de specs/roadmap.md)
**Requisito**: docs/adr/0002-monorepo.md, docs/adr/0003-docker-compose.md, docs/adr/0008-api-fastapi-e-web-separada.md; constituição 3.0.0 (Restrições técnicas)
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O repositório é hoje um pacote Python único. A arquitetura decidida pede um monorepo com um
projeto por aplicação (domínio, CLI, API e web), orquestrado por Docker Compose. Este item
reorganiza o código existente sem mudar o comportamento dos comandos atuais e cria os
esqueletos da API e da web, para que os próximos itens já nasçam no lugar certo.

---

## Cenários de aceite

**Cenário: comandos atuais continuam funcionando**
- **Dado** o repositório reorganizado
- **Quando** o desenvolvedor roda `uv run wordcut --help` e `uv run wordcut overview <arquivo>`
- **Então** os mesmos comandos de antes aparecem e funcionam igual

**Cenário: quality gates da raiz cobrem todos os projetos Python**
- **Dado** o repositório reorganizado
- **Quando** o desenvolvedor roda `uv run pytest`, `uv run ruff check .`,
  `uv run ruff format --check .` e `uv run mypy` da raiz
- **Então** os testes do core, da CLI e da API rodam e tudo passa

**Cenário: web verificável**
- **Dado** o projeto `apps/web`
- **Quando** o desenvolvedor roda a instalação, o typecheck, o lint, os testes e o build
- **Então** tudo passa e o build gera os arquivos estáticos

**Cenário: Compose sobe a aplicação**
- **Dado** o Docker disponível
- **Quando** o desenvolvedor roda `docker compose up -d --build api web`
- **Então** a página da web abre em `http://127.0.0.1:<porta>/` e `GET /api/health` pela mesma
  origem devolve `{"status": "ok"}`

**Cenário: CLI no contêiner**
- **Dado** o Compose construído
- **Quando** o desenvolvedor roda `docker compose run --rm cli --help`
- **Então** a ajuda do `wordcut` aparece

### Casos de borda

- Portas publicadas escutam só em `127.0.0.1`.
- Segredos não entram em imagem nem em contexto de build.
- A fonte da legenda (`assets/fonts`) continua encontrada pelo domínio depois da mudança.
- O worker remoto de transcrição (`asr/remote.py`) continua sincronizando o pacote certo.

---

## Requisitos funcionais

- **FR-001**: O repositório DEVE ter os projetos `packages/core`, `apps/cli`, `apps/api` e
  `apps/web`, cada um com manifesto, código e testes próprios.
- **FR-002**: Os projetos Python DEVEM formar um workspace com um lock único na raiz; o
  executável `wordcut` DEVE vir de `apps/cli`.
- **FR-003**: O domínio atual DEVE morar em `packages/core`, importável como `wordcut`,
  sem depender de nenhuma app.
- **FR-004**: Os comandos atuais da CLI DEVEM continuar com o mesmo comportamento.
- **FR-005**: `apps/api` DEVE expor `GET /api/health` respondendo `{"status": "ok"}`.
- **FR-006**: `apps/web` DEVE compilar uma página inicial do Wordcut que consulta
  `/api/health` e mostra o resultado.
- **FR-007**: `compose.yaml` na raiz DEVE definir `api`, `web` e `cli`, com volume de dados
  compartilhado (`WORDCUT_HOME`), segredos montados só para leitura e portas só em
  `127.0.0.1`; a `web` DEVE repassar `/api` para a `api`.
- **FR-008**: Os quality gates (CONTRIBUTING §3.2) DEVEM passar da raiz.
- **FR-009**: README, CONTRIBUTING e `docs/architecture/` DEVEM refletir a estrutura nova.

---

## Escopo

### Componentes em escopo
- `src/wordcut/` → `packages/core/src/wordcut/` (domínio sem a CLI).
- `src/wordcut/cli.py` → `apps/cli/src/wordcut_cli/`.
- `tests/` → divididos entre `packages/core/tests/` e `apps/cli/tests/`.
- `apps/api/` — esqueleto novo.
- `apps/web/` — esqueleto novo.
- Raiz: `pyproject.toml` (workspace), `uv.lock`, `compose.yaml`, `.dockerignore`,
  `.gitignore`, README, CONTRIBUTING, `docs/architecture/`.

### Fora de escopo
- Mudança de comportamento da CLI (contrato novo é o item 1).
- Camada de serviço, banco, trava.
- Interface real da web (fase 3).
- GPU nos contêineres (depende do NVIDIA Container Toolkit, pendência do administrador).

---

## Pressupostos

- A imagem Python é construída sem o WhisperX por padrão, com um argumento de build para
  incluí-lo; o item de processamento (5) liga a opção.
- O ffmpeg da imagem é o da distribuição base, até o item de processamento verificar se o
  defeito do ffmpeg 6.1 citado no README se aplica.
- `skills/` continua na raiz e segue chamando `uv run wordcut …`.
