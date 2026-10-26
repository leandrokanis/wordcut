# Spec: Rotas da API para pregações, tarefas e estado, com progresso por SSE

**Issue**: web-api-sermons (sem rastreador; item 20a de specs/roadmap.md)
**Requisito**: features 1.1.a–1.1.d, 2.1.b.2, 3.1.a; docs/cli.md §6, §7, §10; ADR-0004,
ADR-0007, ADR-0008, ADR-0013
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A interface web precisa do mesmo que a CLI faz com pregações: criar pelo link, listar,
detalhar (com transcrição), delimitar, processar, pedir nova sugestão, baixar o vídeo e
acompanhar as tarefas e o estado da máquina, com progresso em tempo real. Cada rota chama a
mesma camada de serviço da CLI, com a identidade e as permissões do item 19.

---

## Cenários de aceite

**Cenário: criar e delimitar**
- **Dado** um assistente identificado
- **Quando** ele faz `POST /api/sermons {"url"}` e depois `PATCH /api/sermons/{id}
  {"start", "end"}`
- **Então** recebe a pregação criada (201, ou 200 com `created: false` se já existia) e
  depois a pregação `trimmed`

**Cenário: processar e acompanhar**
- **Dado** uma pregação delimitada e a máquina livre
- **Quando** o assistente faz `POST /api/sermons/{id}/process`
- **Então** recebe `202 {"task_id", …}` e, em `GET /api/tasks/{task_id}/events`, um fluxo SSE
  com eventos `progress` e um `done` (ou `failed`) no fim

**Cenário: máquina ocupada**
- **Dado** outra tarefa segurando a trava
- **Quando** alguém pede processamento
- **Então** recebe `409` com `{"error": {"code": "busy", …}}`

**Cenário: estado e tarefas**
- **Dado** tarefas em andamento
- **Quando** a interface consulta `GET /api/status` e `GET /api/tasks`
- **Então** recebe o mesmo conteúdo de `wordcut status --json` e `wordcut task list --json`

### Casos de borda

- `POST /api/sermons/{id}/suggest` é só de administrador (403 para assistente).
- `GET /api/sermons/{id}/video` envia o arquivo 16:9 com nome legível (`Content-Disposition`);
  pregação não processada → 409 `sermon_not_processed`.
- Cliente que desconecta do SSE não interrompe a tarefa.
- Toda rota exige identidade (exceto `/api/health`).
- Testes nunca chamam YouTube, WhisperX nem o OpenRouter, nem lançam runner real de tipo pesado.

---

## Requisitos funcionais

- **FR-001**: Rotas `GET/POST /api/sermons`, `GET/PATCH /api/sermons/{id}` (com
  `?transcript=true`), `POST /api/sermons/{id}/process` (`force`), `POST
  /api/sermons/{id}/suggest` (admin; `preset_id`), `GET /api/sermons/{id}/video`.
- **FR-002**: Rotas `GET /api/tasks`, `GET /api/tasks/{id}`, `GET /api/tasks/{id}/events`
  (SSE), `GET /api/status`.
- **FR-003**: Tarefas lançadas pela API rodam destacadas (ADR-0007), e a rota devolve 202.
- **FR-004**: Corpos de resposta iguais ao JSON da CLI; erros com o mapeamento HTTP do item 19.
- **FR-005**: Nenhuma regra de negócio na API (ADR-0004).

---

## Escopo

### Componentes em escopo
- `apps/api/src/wordcut_api/` — rotas de pregações, tarefas, estado e SSE.
- `apps/web/nginx.conf` — confirmar `proxy_buffering off` para SSE.

### Fora de escopo
- Rotas de cortes, exportações, configurações, presets e equipe (item 20b).
