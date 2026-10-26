# Spec: Nível 3 — prévia 9:16 sem renderizar, abas Texto e Legenda, grafia na prévia

**Issue**: 1.1.g (web; item 24) · **Requisito**: features 1.1.g.1, 1.1.f (f.2–f.5), Requisitos gerais (aba Legenda); protótipo (nível 3)
**Branch**: `mvp` · **Status**: Draft · **Criado**: 2026-10-26

## Descrição
Dentro de um corte, o assistente vê a prévia 9:16 sem renderizar: o vídeo 16:9 tocando de
trecho em trecho, recortado ao centro do quadro vertical, com a legenda por cima no estilo
do corte. A timeline mostra só o trecho do corte, em tempo do corte. A aba Texto mostra o
texto montado; a aba Legenda traz o formulário de estilo (rótulo à esquerda, controle à
direita), com salvamento automático. Clique duplo numa palavra da legenda, na prévia, abre a
edição da grafia no lugar.

## Cenários de aceite
- **Prévia**: tocar percorre os trechos na ordem, pulando os intervalos; a legenda acompanha
  palavra a palavra com o estilo do corte.
- **Abas**: abre em Texto; clicar na camada de legenda abre Legenda; fechar ou clicar em outra
  área volta para Texto.
- **Estilo**: mudar fonte, tamanho, cor, posição, altura, borda, cor da borda, sombra ou
  ligar/desligar reflete na prévia e salva sozinho; "Restaurar padrão" volta ao estilo da igreja.
- **Grafia**: clique duplo numa palavra pausa o vídeo e abre um campo; Enter ou sair salva
  (ou mostra o bloqueio da trava), Esc cancela.
- **Correções de grafia**: a aba Legenda lista as palavras corrigidas (original → correção);
  Desfazer volta ao original (`PUT` com o texto original).

## Casos de borda
- Trava de grafia: mensagem de bloqueio junto à legenda, sem repetir o texto digitado e sem
  mudar a palavra; o campo continua aberto e Esc fecha.
- Legenda desligada: prévia sem legenda.
- 390 px: layout utilizável.

## Requisitos funcionais
- **FR-001**: Prévia sobre `GET /api/cuts/{id}/preview` e o vídeo da pregação.
- **FR-002**: Legenda desenhada no navegador com o estilo de `GET /api/cuts/{id}/caption`
  (aproximação visual; o resultado final é o da exportação).
- **FR-003**: `PATCH/DELETE /api/cuts/{id}/caption` com autosave; `PUT /api/cuts/{id}/words/{word_id}`.

## Escopo
- `apps/web/src/features/cut/` (nível 3). Fora: exportação (item 25), o botão olho da camada
  Legenda e a alternância 9:16/16:9 do protótipo (o Sim/Não do formulário liga e desliga).
