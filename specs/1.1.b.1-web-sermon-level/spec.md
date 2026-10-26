# Spec: Nível 2 — prévia 16:9, timeline, delimitar e processar

**Issue**: 1.1.b.1 (web; item 22 de specs/roadmap.md)
**Requisito**: features 1.1.b (b.1, b.3), 1.1.c (c.2) e Requisitos gerais de interface;
protótipo `docs/prototype/wordcut.html` (nível 2)
**Branch**: `mvp` · **Status**: Draft · **Criado**: 2026-10-26

## Descrição

Dentro de uma pregação, o assistente vê a prévia 16:9 e a timeline (sempre visíveis),
delimita a pregação puxando as bordas do clipe da live (ou trazendo-as ao cursor com I e O),
processa, e acompanha o progresso. Depois do processamento, as bordas continuam editáveis e
mudá-las oferece Reprocessar.

## Cenários de aceite

**Cenário: delimitar pelas bordas**
- **Dado** uma pregação criada
- **Quando** o assistente arrasta a borda inicial e a final do clipe (ou usa I/O no cursor)
- **Então** a prévia mostra o quadro da borda durante o arraste, a parte cortada fica
  esmaecida, e as bordas são salvas sozinhas (indicador "Salvo")

**Cenário: processar**
- **Dado** bordas definidas (≥ 1 min)
- **Quando** o assistente clica em Processar (no lugar de Exportar)
- **Então** o progresso aparece no botão, por eventos (SSE), e na barra de status, pela
  consulta periódica (ADR-0022); ao fim, a pregação recarrega como processada e o lugar do
  painel de cortes fica pronto para o item 23

**Cenário: reprocessar**
- **Dado** uma pregação processada
- **Quando** o assistente muda as bordas nesta sessão (o `PATCH` responde 200)
- **Então** aparece Reprocessar, com aviso de que as edições dos cortes se perdem; ao
  recarregar a página, ele some, porque a API não diz se as bordas mudaram desde o
  processamento (pendência de API no roadmap)

### Casos de borda
- Máquina ocupada: aviso com o que roda, sem processar.
- Live no ar: com `live_finished: false`, aviso de que a live não terminou, sem travar o
  botão; depois do 409 `live_not_finished`, Processar fica indisponível com o motivo.
- Prévia antes do processamento: a live do YouTube (player incorporado,
  `youtube-nocookie.com`, ADR-0023) no trecho; depois, o vídeo processado servido pela API,
  com o tempo da live convertido para o tempo do vídeo; fora do trecho processado, o YouTube.
- Tarefa em andamento ao abrir a página: o progresso segue pela `last_task`; processamento
  que falhou mostra o motivo e oferece Processar de novo (1.1.c.3).
- Bordas: soltar a borda salva na hora; I/O salvam após 500 ms sem tecla nova. Erro no
  salvamento mostra o motivo, sem "Salvo", e a borda volta ao último valor salvo.
- Timeline sem miniaturas nem forma de onda: a API não as serve (pendência no roadmap); a
  faixa "Vídeo" mostra a live esmaecida e o clipe entre as bordas.

## Requisitos funcionais
- **FR-001**: Prévia 16:9 e timeline sempre visíveis no nível 2, com miniaturas e forma de onda
  quando disponíveis (depois do processamento). Neste item, sem miniaturas nem forma de onda,
  que a API ainda não serve.
- **FR-002**: Bordas arrastáveis e atalhos I/O; salvamento automático via `PATCH`.
- **FR-003**: Processar/Reprocessar com progresso por SSE.

## Escopo
- `apps/web/src/features/sermon/` (nível 2), componentes de timeline e player.
- Fora: painel de cortes (item 23).
