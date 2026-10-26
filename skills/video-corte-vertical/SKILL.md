---
name: video-corte-vertical
description: Revisa e exporta os cortes verticais 9:16 de uma pregação processada pela CLI wordcut — lista os cortes sugeridos, mostra o texto montado e a sequência de trechos, marca os escolhidos, corrige a grafia da legenda e exporta com hesitações e pausas removidas, janela acompanhando o pregador e legenda por palavra. Use quando o usuário pedir corte vertical, Reels, Shorts, TikTok, "sugerir cortes" ou "melhores trechos" de uma pregação.
---

# Cortes verticais de uma pregação

Segunda etapa do fluxo. A primeira é a skill `video-cortar-pregacao`, que deixa a pregação
processada e com cortes sugeridos. A especificação dos comandos está em `docs/cli.md`.

## Pré-requisitos

- Repositório `~/cortes-pregacao` com `uv sync --all-packages`; os comandos abaixo são
  `uv run wordcut …` a partir dele.
- Pregação processada: `uv run wordcut sermon list` mostra o ID e o estado `processed`.
  Se não estiver, rode a primeira etapa antes.
- Cortes sugeridos: `uv run wordcut sermon show <id>` mostra os cortes e o erro da última
  sugestão. Sem cortes por falta de modelo ou chave do LLM, peça ao administrador para
  configurá-los (`settings set`, `settings set-key`) e pedir uma nova sugestão.

## Fluxo

1. **Ver os cortes**: `uv run wordcut cut list --sermon <id>`. Os critérios da sugestão são
   os do preset (`uv run wordcut criteria list`, `uv run wordcut preset show <preset>`);
   esta skill não aplica critério próprio. Outra sugestão, com outro preset, é
   `uv run wordcut sermon suggest <id> --preset <preset> --wait`.
2. **Mostrar cada corte em texto** com `uv run wordcut cut preview <corte>`: a sequência de
   trechos, com `↑` no que volta no tempo. O usuário decide; nada é exportado sem aprovação.
3. **Registrar a decisão**: `uv run wordcut cut choose <corte>` ou
   `uv run wordcut cut discard <corte>` (`cut restore` desfaz o descarte).
4. **Ajustar a legenda**, se preciso: `uv run wordcut cut show <corte>` lista as palavras com
   `word_id`; `uv run wordcut cut fix-word <corte> <word_id> <texto>` corrige a grafia só
   neste corte; `uv run wordcut cut caption <corte>` mostra ou troca o estilo.
5. **Exportar** cada corte escolhido (tarefa com trava):
   ```
   uv run wordcut cut render <corte> --estimate
   uv run wordcut cut render <corte> --wait --json
   ```
   As opções (`--fillers`, `--stammers`, `--pauses`, `--resolution`, `--quality`,
   `--smooth-joins`, `--fade`, `--normalize`, `--caption`) ficam salvas no corte. Se a
   máquina estiver ocupada (saída 4), espere a tarefa de `uv run wordcut status` com
   `uv run wordcut task wait <task_id>`.
6. **Relatar**: título, duração e caminho de cada exportação. Lembre o usuário de assistir
   antes de publicar.

## Onde ver o resultado

- `uv run wordcut render list --cut <corte>`: as exportações do corte, com o caminho local.
- `uv run wordcut render download <exportação> -o <pasta>/`: copia o vídeo com nome legível
  (data do culto e título do corte), sem sobrescrever, e mostra o caminho.

## Regras

- Não descarte, reprocesse nem apague nada sem o "ok" do usuário.
- A sugestão é do LLM com os critérios do preset; publicar é decisão do usuário, após assistir.
- Não registre nomes de pessoas em relatórios (LGPD).
