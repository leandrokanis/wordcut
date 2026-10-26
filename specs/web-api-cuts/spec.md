# Spec: Rotas da API para cortes, exportações, configurações, presets e equipe

**Issue**: web-api-cuts (sem rastreador; item 20b de specs/roadmap.md)
**Requisito**: features 1.1.e–1.1.i, 1.2.a, 2.1.a; docs/cli.md §8, §9, §11, §12; ADR-0004
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A interface web precisa de todas as operações de cortes (listar, detalhar, prévia, escolher,
descartar, restaurar, corrigir grafia, estilo da legenda, exportar com estimativa), das
exportações (listar, detalhar, baixar), das configurações (sem nunca devolver segredo),
dos critérios e presets e da equipe, com as permissões da 1.2.a.

---

## Cenários de aceite

**Cenário: escolher e ajustar um corte**
- **Dado** um assistente e um corte sugerido
- **Quando** ele faz `POST /api/cuts/{id}/choose`, `PUT /api/cuts/{id}/words/{word_id}
  {"text"}` e `PATCH /api/cuts/{id}/caption {…}`
- **Então** recebe o corte escolhido, a correção aplicada (ou 409 `spelling_too_different`) e
  o estilo novo

**Cenário: exportar**
- **Dado** um corte e a máquina livre
- **Quando** o assistente faz `POST /api/cuts/{id}/renders {opções}`
- **Então** recebe 202 com a tarefa; `GET /api/cuts/{id}/renders/estimate?…` devolve a
  estimativa sem tarefa

**Cenário: baixar exportação**
- **Dado** uma exportação
- **Quando** alguém faz `GET /api/renders/{id}/file`
- **Então** recebe o arquivo com nome legível

**Cenário: configurações e equipe só para administrador**
- **Dado** um assistente
- **Quando** ele chama `/api/settings`, `/api/presets` (escrita) ou `/api/members`
- **Então** recebe 403; o administrador recebe o mesmo JSON da CLI

### Casos de borda

- `PUT /api/settings/llm-key` e `PUT /api/settings/youtube-cookies` recebem o segredo no corpo
  e respondem só a máscara/presença; o segredo nunca volta.
- Edição de conteúdo (segments) não existe nesta onda.
- Testes sem rede e sem renderização real.

---

## Requisitos funcionais

- **FR-001**: Rotas de cortes: `GET /api/sermons/{id}/cuts`, `GET /api/cuts/{id}`,
  `GET /api/cuts/{id}/preview`, `POST /api/cuts/{id}/{choose|discard|restore}`,
  `PUT /api/cuts/{id}/words/{word_id}`, `GET/PATCH/DELETE /api/cuts/{id}/caption`,
  `POST /api/cuts/{id}/renders`, `GET /api/cuts/{id}/renders/estimate`.
- **FR-002**: Exportações: `GET /api/cuts/{id}/renders`, `GET /api/renders/{id}`,
  `GET /api/renders/{id}/file`.
- **FR-003**: Admin: `GET/PATCH /api/settings`, `PUT /api/settings/llm-key`,
  `PUT /api/settings/youtube-cookies`, `GET /api/criteria`, `/api/presets` (CRUD e
  `set-default`), `/api/members` (CRUD).
- **FR-004**: Corpos iguais ao JSON da CLI; segredos nunca devolvidos.
- **FR-005**: Permissões da tabela da 1.2.a.

---

## Escopo

### Componentes em escopo
- `apps/api/src/wordcut_api/routes/` — cortes, exportações, configurações, critérios, presets,
  membros.

### Fora de escopo
- Edição de conteúdo (onda 6).
