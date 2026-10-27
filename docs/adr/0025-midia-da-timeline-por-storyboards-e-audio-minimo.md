# ADR-0025: Mídia da timeline por storyboards e áudio mínimo, numa tarefa sem trava

**Status**: Aceita · **Data**: 2026-10-27

Complementa a [ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md), cujo padrão
de porta substituível repete, a [ADR-0007](0007-tarefas-em-processo-destacado.md), que ganha
um tipo de tarefa sem trava lançado pela criação da pregação, e a
[ADR-0017](0017-testes-sem-rede-real.md), cuja guarda vale para a porta nova (item 1.1.b.1,
[#9](https://github.com/leandrokanis/wordcut/issues/9)).

## Contexto

A timeline do nível da pregação mostrava só a faixa do vídeo, lisa. Para achar o início e o
fim da pregação sem assistir à live, o assistente precisa de miniaturas da live na faixa
"Vídeo" e da forma de onda numa faixa "Áudio", como no protótipo — antes de processar, que é
quando as bordas são marcadas. Baixar o vídeo da live inteira (duas horas) para tirar
miniaturas custa gigabytes e minutos.

O YouTube oferece imagens de navegação (storyboards): grades de miniaturas da live inteira.
O yt-dlp as lista como formatos `sbN` no JSON do `--dump-single-json`
(`yt_dlp/extractor/youtube/_video.py`, `_extract_storyboard`): tamanho de uma miniatura,
colunas e linhas da grade, miniaturas por segundo e as URLs das grades. A forma de onda só
precisa de quão alto é o áudio, que a menor qualidade dá.

## Decisão

- **Porta `TimelineMediaGateways`** (`wordcut.timeline_media`): `storyboard(url, out_dir)`
  devolve a faixa de miniaturas ou `None`, `audio(url, output)` baixa só o áudio da live
  inteira (`-f worstaudio`) e `peaks(audio, buckets)` calcula os picos. `default_gateways()`
  monta a real (yt-dlp, `httpx` para as grades, `ffmpeg`) e recusa com `network_error` sob
  `WORDCUT_FORBID_NETWORK`; a suíte a troca por uma que falha (`no_real_timeline_media`).
- **Miniaturas do maior storyboard.** A faixa sai do formato `sbN` de maior área, com no
  máximo 240 miniaturas espaçadas igualmente no tempo, lado a lado num JPEG, e um JSON com o
  tamanho de uma miniatura e o segundo de cada uma. Só as grades usadas são baixadas.
- **Picos de 4000 baldes**, o maior valor absoluto de cada trecho igual da live, lidos do
  PCM mono de 8 kHz do `ffmpeg` em blocos (a live não fica inteira na memória) e
  normalizados pelo maior; silêncio dá zeros. O áudio é apagado depois dos picos.
- **Tarefa `prepare`, sem trava.** Não usa GPU e não atrapalha o processamento; roda junto
  com `process` e `render`. Uma por pregação: outra em andamento recusa com `busy` e o
  `task_id` dela. `sermon create` a lança destacada numa pregação nova, pela
  `tasks.execution`; `sermon prepare` e `POST /api/sermons/{id}/prepare` a pedem de novo, e
  refazem mesmo uma timeline pronta. Mostrar a pregação nunca prepara.
- **Estado na tabela `timeline_media`** (migração 0012): `pending`, `ready` ou `failed`, com
  o erro. A leitura confere: `pending` sem tarefa viva, ou pregação sem linha (criada antes
  da migração), aparece `failed` com `interrupted`, pronta para tentar de novo. `sermon show`
  traz `timeline: {status, error, task_id}`; `last_task` deixa a `prepare` de fora, e ela não
  conta como processamento em andamento.
- **Falha parcial.** Storyboard ausente ou com falha deixa a timeline `ready` só com a onda;
  só a falha do áudio a deixa `failed`. A mensagem é genérica e nunca traz o texto da falha,
  que pode ter caminho ou o arquivo de cookies.
- **Arquivos em `media/sermons/<id>/timeline/`**, gravados ao lado e renomeados. A API os
  serve em `GET …/thumbnails` (JPEG), `…/thumbnails.json` e `…/waveform`, com 404 quando
  não existem.
- **Web.** As faixas "Vídeo" e "Áudio" seguem o `timeline()` do protótipo: a imagem da live
  inteira esmaecida atrás (`data-faded`) e, no clipe, o recorte dela entre as bordas
  (`innerBg`). A onda é um SVG desenhado a partir dos picos. Enquanto a preparação roda, as
  faixas ficam lisas com "Preparando a timeline…"; a web acompanha a tarefa pelos eventos
  (SSE) e, no fim, lê a pregação e as mídias de novo, sem polling. A falha mostra um aviso e
  "Tentar de novo".

## Consequências

- A timeline mostra a live antes de processar, sem baixar vídeo; uma live de duas horas custa
  dezenas de MB de áudio, apagado em seguida, e algumas grades de imagem.
- Toda criação de pregação lança um processo. Na suíte, o `conftest.py` da raiz faz as
  tarefas destacadas rodarem um processo inofensivo quando o teste não pede
  `detached_tasks` nem `harmless_tasks` (`harmless_tasks_unless_asked`); com
  `detached_tasks`, a `prepare` real recusa pela guarda de rede.
- Os testes que contam tarefas ou processos lançados passam a filtrar pelo tipo ou a contar
  depois da criação.
- Se o YouTube mudar o formato dos storyboards, só o `storyboard.py` muda, e a falha deixa a
  faixa de vídeo lisa.
