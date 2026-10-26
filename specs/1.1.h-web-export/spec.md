# Spec: Caixa de exportação e downloads na web

**Issue**: 1.1.h (web; item 25) · **Requisito**: features 1.1.h (h.1, h.3), 1.1.i (i.1); protótipo (diálogo de exportação)
**Branch**: `mvp` · **Status**: Draft · **Criado**: 2026-10-26

## Descrição
No nível 3, Exportar abre uma caixa com as opções (limpeza, edição, áudio, legenda, vídeo) e
a duração estimada, que se atualiza a cada mudança. Confirmar inicia a exportação, com
progresso no botão e na barra de status. Cada exportação fica no corte, com data, duração e
resumo das opções, e pode ser baixada.

## Cenários de aceite
- **Opções e estimativa**: a caixa abre com as últimas opções do corte; mudar uma opção
  atualiza a duração estimada.
- **Exportar**: confirmar inicia a tarefa; progresso por eventos; ao fim, a exportação aparece
  na lista do corte.
- **Baixar**: cada exportação tem Baixar, que entrega o arquivo com nome legível.

## Casos de borda
- Máquina ocupada: aviso, sem exportar.
- Falha: mensagem com o motivo; nenhuma exportação nova.

## Requisitos funcionais
- **FR-001**: Caixa sobre `GET /api/cuts/{id}/renders/estimate` e `POST /api/cuts/{id}/renders`.
- **FR-002**: Lista de exportações (`GET /api/cuts/{id}/renders`) com Baixar (`/api/renders/{id}/file`).

## Escopo
- `apps/web/src/features/cut/ExportDialog.tsx`, `RendersList.tsx`.
