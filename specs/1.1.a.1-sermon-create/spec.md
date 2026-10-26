# Spec: Criar pregação pelo link e consultá-la (`sermon create`, `list`, `show`)

**Issue**: 1.1.a.1 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.a-create-sermon-from-link.md §1.1.a.1, §1.1.a.2;
docs/cli.md §3.3, §7.1, §7.2
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente (ou um agente) cola o link da live do culto e quer confirmar que é o culto
certo: título, data do culto e duração. A pregação passa a existir no sistema com um ID
estável, pode ser listada e consultada. Repetir o mesmo link não cria duplicata, e uma live
que ainda não terminou é aceita com aviso.

---

## Cenários de aceite

**Cenário: criar pela primeira vez**
- **Dado** um link de live terminada que ainda não foi cadastrada
- **Quando** o operador roda `wordcut sermon create <link> --json`
- **Então** o JSON traz `id`, `title`, `service_date`, `live_duration`, `live_finished: true`,
  `status: "created"` e `created: true`, e a saída é 0

**Cenário: mesmo vídeo de novo (idempotente)**
- **Dado** uma pregação já criada a partir de um vídeo
- **Quando** o operador roda `sermon create` com outro link do mesmo vídeo
  (`watch?v=`, `youtu.be/`, `/live/`)
- **Então** a resposta é a pregação existente, com `created: false` e saída 0

**Cenário: live ainda no ar (1.1.a.2)**
- **Dado** uma live que não terminou
- **Quando** o operador cria a pregação
- **Então** ela é criada com `live_finished: false` e um aviso vai para o stderr

**Cenário: listar**
- **Dado** pregações criadas
- **Quando** o operador roda `wordcut sermon list --json`
- **Então** recebe `{"items": [...]}` com ID, título, data, estado e contagem de cortes por
  estado, da mais recente para a mais antiga; `--status` filtra

**Cenário: detalhar**
- **Dado** uma pregação criada
- **Quando** o operador roda `wordcut sermon show <id> --json`
- **Então** recebe os dados da pregação, as bordas (vazias por enquanto) e a lista de cortes
  (vazia por enquanto)

### Casos de borda

- Link que não é do YouTube ou sem ID de vídeo → `invalid_argument` (saída 2), sem consultar
  o YouTube.
- Falha do YouTube (vídeo inexistente, rede) → `youtube_error` (saída 6), sem criar nada.
- `sermon show` de ID inexistente → `not_found` (saída 3).
- Vídeo sem horário de início → `youtube_error` com mensagem clara.
- Sem `--json`, a saída é um resumo legível em português.

---

## Requisitos funcionais

- **FR-001**: `sermon create <link>` DEVE consultar os dados da live e gravar a pregação com
  ID inteiro estável, ID do vídeo, link, título, data do culto, duração da live, se terminou,
  estado `created` e data de criação.
- **FR-002**: O ID do vídeo DEVE ser extraído do link nos formatos `watch?v=`, `youtu.be/`,
  `/live/` e `/shorts/`; o mesmo vídeo DEVE devolver a pregação existente com
  `created: false`, sem nova consulta ao YouTube.
- **FR-003**: Live não terminada DEVE ser criada com `live_finished: false` e aviso no stderr.
- **FR-004**: `sermon list` DEVE listar as pregações da mais recente para a mais antiga, com
  filtro opcional `--status`.
- **FR-005**: `sermon show <id>` DEVE devolver a pregação com bordas e cortes.
- **FR-006**: Todos os comandos DEVEM seguir o contrato de docs/cli.md §4 e §5 (item 1).
- **FR-007**: A regra de negócio DEVE ficar na camada de serviço do core; a CLI só traduz
  argumentos e saída (ADR-0004).

---

## Entidades e dados

- **Pregação (`sermon`)**: id, youtube_id (único), url, title, service_date, live_duration,
  live_finished, status (`created` | `trimmed` | `processing` | `processed` | `failed`),
  live_start e live_end (bordas, vazias até o `trim`), created_at, updated_at.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — serviço de pregações, migração da tabela, uso de
  `youtube.py` para os dados da live.
- `apps/cli/src/wordcut_cli/` — subcomandos `sermon create`, `list`, `show`.
- `packages/core/tests/`, `apps/cli/tests/` — testes com o YouTube como dublê.

### Fora de escopo
- `--start`, `--end` e `--process` do `create` (itens 3 e 5).
- `sermon show --transcript` (item 5).
- Cortes reais (item 9 em diante): a lista de cortes vem vazia.

### Integrações externas
- YouTube, via `yt-dlp` (dublê nos testes).

---

## Pressupostos

- A data do culto segue a regra existente de `LiveInfo` (fuso da igreja).
- Os cookies do YouTube vêm de `WORDCUT_CONFIG` (ou `~/.config/wordcut`) e nunca aparecem em
  saída.
