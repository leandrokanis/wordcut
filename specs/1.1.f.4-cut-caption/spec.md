# Spec: Estilo da legenda de um corte (`cut caption`)

**Issue**: 1.1.f.4 (sem rastreador; o ID é o código do requisito)
**Requisito**: docs/requirements/features/1.1.f-adjust-form.md §1.1.f.4, §1.1.f.5; docs/cli.md §8.6
**Branch**: `mvp` (branch única da execução automatizada)
**Status**: Draft
**Criado**: 2026-10-26

---

## Descrição

O assistente ajusta o estilo da legenda de um corte (fonte, tamanho, cor, posição, altura,
borda, cor da borda e sombra) ou a desliga. O estilo vale para todas as legendas do corte e
é o que a exportação vai usar. O padrão é o estilo da igreja.

---

## Cenários de aceite

**Cenário: ver o estilo padrão**
- **Dado** um corte novo
- **Quando** o assistente roda `wordcut cut caption <id> --json`
- **Então** recebe `{"enabled": true, "font": "Open Sans Bold", "size": 60, "color": "#FFD600",
  "position": "center", "offset": 50, "border": 3, "border_color": "#000000", "shadow": "soft"}`

**Cenário: mudar o estilo**
- **Dado** um corte
- **Quando** o assistente roda `cut caption <id> --size 72 --color "#FFFFFF" --position bottom --shadow strong`
- **Então** só esses campos mudam e o `cut show` mostra o novo estilo

**Cenário: desligar e restaurar**
- **Dado** um corte com estilo alterado
- **Quando** o assistente roda `cut caption <id> --off` e depois `--reset`
- **Então** a legenda fica desligada e depois volta ao padrão da igreja (ligada)

**Cenário: estilo vira imagem**
- **Dado** um estilo com fonte, tamanho, cor, borda, cor da borda e sombra
- **Quando** uma legenda é desenhada
- **Então** a imagem usa exatamente esse estilo e fica na altura da posição escolhida

### Casos de borda

- Fonte que não existe no pacote → `invalid_argument` com as fontes disponíveis em `details`.
- Cor fora de `#RRGGBB` → `invalid_argument`.
- Tamanho (24–160 px), altura (10–90 %) ou borda (0–12 px) fora da faixa → `invalid_argument`.
- `--on` e `--off` juntos, ou `--reset` com outra opção → `invalid_argument`.
- Corte inexistente → `not_found`.

---

## Requisitos funcionais

- **FR-001**: O estilo DEVE ficar gravado no corte; ausência de estilo DEVE significar o padrão.
- **FR-002**: `cut caption` sem opções DEVE mostrar o estilo; com opções, DEVE alterar só o informado.
- **FR-003**: `--reset` DEVE voltar ao padrão; `--off`/`--on` DEVEM desligar e ligar.
- **FR-004**: O desenho da legenda DEVE aplicar fonte, tamanho, cor, borda, cor da borda, sombra
  (nenhuma, suave, forte) e posição/altura.

---

## Escopo

### Componentes em escopo
- `packages/core/src/wordcut/` — modelo do estilo, validação, serviço, desenho da legenda.
- `apps/cli/src/wordcut_cli/cut.py` — `caption`.

### Fora de escopo
- Exportação (item 15).
- Fontes além das incluídas no pacote.

---

## Pressupostos

- As posições valem `top` = 20 %, `center` = 50 % e `bottom` = 78 % da altura do quadro, como
  no protótipo (docs/prototype/wordcut.html); `--offset` (10–90 %) é a altura final, vence
  `--position` quando os dois vêm juntos e, sozinho, mantém o `position`.
- As fontes disponíveis são as de `packages/core/src/wordcut/assets/fonts/` (hoje Open Sans
  Bold, licença OFL).
