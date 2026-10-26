---
name: video-cortar-pregacao
description: Extrai a pregação de uma live de culto no YouTube pela CLI wordcut — cria a pregação a partir do link, delimita início e fim em tempo da live e processa (baixa só a faixa, transcreve com o WhisperX, ajusta as bordas às palavras e corta em 16:9 com fades). Use quando o usuário passar o link de uma live/culto e pedir para recortar, cortar ou extrair a pregação/sermão, com ou sem minutagem.
---

# Extrair a pregação de uma live

Primeira etapa do fluxo. A segunda é a skill `video-corte-vertical`, que trabalha com os
cortes da pregação processada aqui. A especificação dos comandos está em `docs/cli.md`.

## Pré-requisitos

- Repositório `~/cortes-pregacao` com `uv sync --all-packages`; os comandos abaixo são
  `uv run wordcut …` a partir dele.
- Máquina com GPU e o ambiente do WhisperX (README, seção Instalação).
- Cookies do YouTube gravados: `uv run wordcut settings show` mostra se há cookies. Se não
  houver, peça ao administrador para gravá-los com `settings set-cookies` e pare.
- Para os cortes sugeridos: modelo e chave do LLM em `settings show`. Sem eles a pregação é
  processada sem cortes; avise o usuário.

## Entradas

- **Link da live** (obrigatório).
- **Início e fim aproximados da pregação** em tempo da live (`HH:MM:SS`). Sem eles, peça ao
  usuário; o processamento ajusta as bordas à primeira e à última palavra dentro da faixa.

## Fluxo

1. **Criar**: `uv run wordcut sermon create <link> --json`. Mostre título, data do culto e
   duração. Se `live_finished` for `false`, avise que a live ainda está no ar e pare.
2. **Delimitar e processar** (tarefa com trava; leva alguns minutos):
   ```
   uv run wordcut sermon trim <id> --start <início> --end <fim> --json
   uv run wordcut sermon process <id> --wait --json
   ```
   Com as bordas já conhecidas, os passos 1 e 2 cabem num só:
   `uv run wordcut sermon create <link> --start <início> --end <fim> --process --wait --json`.
   Se a máquina estiver ocupada (saída 4), `uv run wordcut status` diz qual tarefa segura a
   trava; espere por `uv run wordcut task wait <task_id>`.
3. **Conferir as bordas**: `uv run wordcut sermon show <id> --transcript`. A primeira frase
   deve ser a do pregador e a última, o fim da pregação (sem apelo, avisos ou louvor
   conduzidos por outra pessoa). Bordas erradas: `sermon trim` com os tempos corrigidos e
   `sermon process <id> --force --wait`, que descarta transcrição e cortes.
4. **Relatar**: título, data, duração, bordas e quantos cortes foram sugeridos. Sugira seguir
   para os cortes verticais.

## Onde ver o resultado

- `uv run wordcut sermon show <id>`: bordas na live, duração, estado, cortes e o erro da
  sugestão, se houver.
- `uv run wordcut sermon download <id> -o <pasta>/`: copia a pregação 16:9 com nome legível
  (data e título), sem sobrescrever, e mostra o caminho.

## Regras

- Nunca exiba, copie ou registre cookies ou chave; eles só entram pelo stdin dos comandos de
  `settings`.
- O resultado é sugestão: o usuário assiste ao início e ao fim antes de publicar.
- Não registre nomes de pessoas em relatórios (LGPD).
