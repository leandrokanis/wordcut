# Contribuindo com o Wordcut

Este guia vale para pessoas e agentes. As palavras-chave DEVE, NÃO DEVE, DEVERIA e PODE
seguem o BCP 14 ([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119),
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)).

## 1. Onde está cada coisa

| Documento | Conteúdo |
|---|---|
| [docs/constitution.md](docs/constitution.md) | princípios e restrições de arquitetura |
| [docs/requirements/](docs/requirements/features.md) | o que a aplicação faz (prevalece em funcionalidade) |
| [docs/adr/](docs/adr/README.md) | decisões de arquitetura, uma por arquivo |
| [docs/architecture/](docs/architecture/README.md) | modelo C4 e diagramas de sequência |
| [docs/cli.md](docs/cli.md) | especificação da CLI |
| [specs/](specs/roadmap.md) | specs, planos e QA de cada item em desenvolvimento |

## 2. Organização do repositório

Monorepo com um projeto por aplicação ([ADR-0002](docs/adr/0002-monorepo.md)), orquestrado
por Docker Compose ([ADR-0003](docs/adr/0003-docker-compose.md)):

```
packages/core/   domínio e camada de serviço (Python, pacote `wordcut`)
apps/cli/        CLI `wordcut` (Python, pacote `wordcut_cli`)
apps/api/        API HTTP (Python, FastAPI, pacote `wordcut_api`)
apps/web/        interface (React + Vite + TypeScript)
```

Regra de dependência: `apps/*` dependem de `packages/core`; `packages/core` não depende de
nenhuma app; apps não dependem umas das outras. Regra de negócio vive só no `core`.

## 3. Fluxo de trabalho

- XP: entregas pequenas, TDD (vermelho → verde → refatorar), integração contínua na branch,
  design simples, refatoração constante e propriedade coletiva do código.
- Cada item segue `/dev-specify` → `/dev-plan` → `/dev-implement-qa` (ver
  [specs/roadmap.md](specs/roadmap.md)).
- Testes de comportamento pela interface pública. Serviço externo (YouTube, WhisperX,
  OpenRouter) é dublê nos testes.
- A suíte não usa a rede real. O `conftest.py` da raiz define `WORDCUT_FORBID_NETWORK`, que
  todo processo lançado pelo teste herda, inclusive uma tarefa destacada. Com ela definida,
  `suggestion.default_model` e `processing.default_gateways` recusam com `network_error`
  ([ADR-0017](docs/adr/0017-testes-sem-rede-real.md)). Um teste que precise da tarefa
  `running` usa `harmless_tasks`.
- A suíte não renderiza vídeo real. A fixture `no_real_rendering` faz
  `rendering.default_gateways` falhar, e nenhum teste lança um `render` destacado de verdade
  ([ADR-0018](docs/adr/0018-exportacao-por-portas-sem-arquivo-parcial.md)). O único `ffmpeg`
  real é o de clipes sintéticos curtos.

### 3.1. Decisões de arquitetura

- Toda decisão de arquitetura DEVE virar uma ADR em `docs/adr/`, com entrada no índice.
- ADR aceita não é editada; uma decisão nova a substitui e as duas apontam uma para a outra.
- Quando a arquitetura muda, os documentos DEVEM ser atualizados no mesmo commit:
  `docs/architecture/` (C4 e diagramas de sequência em Mermaid), este guia e o README.

### 3.2. Quality gates

Antes de integrar, tudo limpo, da raiz (depois de `uv sync --all-packages` e
`npm --prefix apps/web ci`):

```sh
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
npm --prefix apps/web test
npm --prefix apps/web run typecheck && npm --prefix apps/web run lint
npm --prefix apps/web run build
```

`uv run mypy` verifica `packages/core/src`, `apps/cli/src` e `apps/api/src` (lista em
`pyproject.toml`). Mudança em `compose.yaml` ou num `Dockerfile` também passa por
`docker compose config -q` e `docker compose build api web cli`.

### 3.3. Commits

- Mensagem em inglês, no imperativo, com o assunto em até 72 caracteres.
- Um commit por mudança lógica.

## 4. Código

- Clean code: nomes que revelam intenção, funções pequenas que fazem uma coisa, sem
  duplicação, sem código morto, sem número mágico.
- Código, identificadores e comentários em inglês. Texto voltado ao usuário em português.
- Python ≥ 3.10, tipado (`mypy --strict`), formatado com `ruff format`.
- TypeScript estrito, formatado e verificado pelo lint do `apps/web`.

## 5. Comentários

Todo comentário DEVE pertencer a um dos tipos desta seção. Comentário que não pertence a
nenhum DEVE ser removido. Se o comentário explica um código pouco claro, o código DEVERIA
ser reescrito no lugar do comentário.

Comentários são escritos em inglês.

### 5.1. Intenção

Diz por que o código é assim quando o código não mostra o motivo. Em geral, o motivo é uma
escolha entre alternativas.

```python
# Retry once only: a second retry lets the operator start a scan on stale data.
```

### 5.2. Alerta

Diz a consequência de uma mudança que parece segura.

```python
# Do not close the socket here. The detector reuses it for the next rotation.
```

### 5.3. Restrição externa

Diz uma regra que vem de fora do código: uma norma, o hardware ou um serviço parceiro. O
comentário DEVE identificar a fonte.

```ts
// DICOM PS3.3 C.7.6.2: Image Position (Patient) is in mm, in LPS coordinates.
```

### 5.4. Contorno

Diz por que o código desvia de um defeito numa dependência. O comentário DEVE trazer o link
da issue pública dessa dependência, para que alguém remova o contorno quando a issue fechar.

```ts
// Vite drops the worker on reload: https://github.com/vitejs/vite/issues/NNNNN
```

### 5.5. Referência

Aponta para uma ADR ou para um documento de `docs/` que explica a decisão.

```python
# The scout frame is the encoder frame, see ADR-004.
```

### 5.6. Formato

Diz uma unidade, a referência de uma medida, o sentido de uma expressão regular ou um layout
de bits.

Se o identificador comporta a informação, o identificador DEVE levá-la e o comentário NÃO
DEVE ser escrito. Por exemplo, `offset_mm` ou `timeoutMs`, e não um comentário que diz
"em mm".

```python
# Bits 0-3: tube state. Bits 4-7: door interlock.
```

### 5.7. Contrato público

Documenta uma interface para quem não lê a implementação. Por exemplo, um módulo que outro
app importa ou o contrato de um serviço. É o único tipo que PODE ser longo.

### 5.8. Diretiva de ferramenta

Uma diretiva que uma ferramenta lê, como `eslint-disable`, `noqa`, `type: ignore` ou
`@ts-expect-error`. A diretiva que desliga uma verificação DEVE dizer o motivo na mesma
linha ou na linha de cima.

```ts
// eslint-disable-next-line react-hooks/exhaustive-deps -- runs once on mount
```

O comentário mágico que a linguagem lê, como shebang, linha de encoding ou
`// @vitest-environment jsdom`, não precisa de motivo.

### 5.9. Aviso legal

Um aviso que uma licença ou um contrato exige.

## 6. Segurança e privacidade

Ver [SECURITY.md](SECURITY.md) e a constituição §VI. Segredos nunca entram no repositório,
em log, em saída ou em mensagem de erro. Exemplos e testes usam dados fictícios, sem nomes
de pessoas.
