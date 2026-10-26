# Spec: Nível 2 — painel de cortes

**Issue**: 1.1.e (web; item 23) · **Requisito**: features 1.1.e (e.1, e.2), 2.1.c (camadas, só leitura nesta onda); protótipo (cards de corte)
**Branch**: `mvp` · **Status**: Draft · **Criado**: 2026-10-26

## Descrição
Na pregação processada, o assistente vê os cortes sugeridos num painel lateral (cards simples
com título, texto montado e duração) e cada corte como uma faixa numa camada própria da
timeline. Abrir um corte sugerido já o marca como escolhido; descartar e restaurar ficam num
menu secundário; os descartados vão para o fim.

## Cenários de aceite
- **Listar**: cards com título, texto, duração e estado; descartados por último.
- **Abrir**: clicar num card abre o nível 3 e marca o corte como escolhido.
- **Descartar/restaurar**: pelo menu do card; o card vai para o fim (ou volta).
- **Camadas**: cada corte aparece como faixa contínua na timeline do nível 2 (só leitura).

## Casos de borda
- Pregação sem cortes, com `suggestion_error`: mensagem com o motivo (ex.: LLM não configurado).
- Nenhuma edição de conteúdo nesta onda.

## Requisitos funcionais
- **FR-001**: Painel de cortes sobre `GET /api/sermons/{id}/cuts`.
- **FR-002**: `choose` ao abrir; `discard`/`restore` no menu.
- **FR-003**: Camadas de cortes na timeline, sem edição.

## Escopo
- `apps/web/src/features/sermon/CutsPanel.tsx`, `CutCard.tsx`, camadas na `Timeline`.
