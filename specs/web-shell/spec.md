# Spec: Esqueleto da interface web, lista de pregações e Nova pregação

**Issue**: web-shell (sem rastreador; item 21 de specs/roadmap.md)
**Requisito**: docs/requirements/features.md (Requisitos gerais de interface); feature 1.1.a
(web); protótipo `docs/prototype/wordcut.html`; ADR-0008
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

A equipe abre o Wordcut no navegador e vê a lista de pregações (nível 1), cria uma pregação
colando o link da live, e navega pelo caminho no topo entre os três níveis. A barra de
status no rodapé mostra sempre o estado da máquina. As configurações ocupam a tela inteira,
com navegação própria (conteúdo no item 26). A aparência segue o protótipo.

---

## Cenários de aceite

**Cenário: lista de pregações**
- **Dado** pregações cadastradas
- **Quando** o usuário abre a aplicação
- **Então** vê a lista (nível 1) com título, data do culto, duração e estado, sem prévia nem
  timeline, e o caminho no topo mostra "Pregações"

**Cenário: Nova pregação**
- **Dado** a lista de pregações
- **Quando** o usuário clica em "Nova pregação", cola o link e confirma
- **Então** a pregação aparece com título, data e duração vindos da live; se a live não
  terminou, um aviso aparece; se o link for inválido, o motivo aparece junto ao campo

**Cenário: navegação pelo caminho**
- **Dado** o usuário dentro de uma pregação (nível 2) ou de um corte (nível 3)
- **Quando** clica num item do caminho no topo
- **Então** volta ao nível correspondente; "Nova pregação" só existe no nível 1

**Cenário: barra de status**
- **Dado** qualquer tela
- **Quando** uma tarefa está em andamento ou a máquina está livre
- **Então** o rodapé mostra o estado (livre, ou o que roda e o progresso), atualizado sozinho

**Cenário: configurações**
- **Dado** um administrador
- **Quando** abre Configurações
- **Então** vê uma tela inteira com navegação própria (seções no item 26); assistente não vê a
  entrada

### Casos de borda

- API fora do ar: mensagem clara, sem tela em branco.
- Lista vazia: estado vazio com a ação "Nova pregação".
- Sem identidade (401) ou fora da equipe (403): tela explicando, sem dados.
- Layout funciona em 390 px de largura sem rolagem horizontal.

---

## Requisitos funcionais

- **FR-001**: Rotas da SPA: `/` (Pregações), `/sermons/:id` (Pregação), `/cuts/:id` (Corte),
  `/settings` (Configurações).
- **FR-002**: Caminho no topo com os três níveis e navegação por clique.
- **FR-003**: Lista de pregações e diálogo "Nova pregação" sobre a API (item 20a).
- **FR-004**: Barra de status no rodapé, sempre visível, atualizada por consulta periódica a
  `/api/status` (e pelos eventos quando houver tarefa). Neste item, só a consulta periódica
  de 3 s; os eventos SSE entram no item 22, a tela que acompanha a tarefa.
- **FR-005**: Indicador "Salvo" reutilizável para os formulários de salvamento automático.
- **FR-006**: Visual do protótipo (tokens de cor e tipografia), tema escuro de editor.

---

## Escopo

### Componentes em escopo
- `apps/web/src/` — roteamento, cliente da API tipado, layout, nível 1, diálogo, barra de
  status, página de configurações vazia.

### Fora de escopo
- Níveis 2 e 3 (itens 22–25) e conteúdo das configurações (item 26).
