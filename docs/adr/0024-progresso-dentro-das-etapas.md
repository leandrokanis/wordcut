# ADR-0024: Progresso dentro das etapas do processamento

**Status**: Aceita · **Data**: 2026-10-27

Complementa a [ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md), cujas portas
de download e de transcrição ganham um retorno de andamento, e a
[ADR-0007](0007-tarefas-em-processo-destacado.md), no limite de gravação do progresso
(item 1.1.c.2, [#3](https://github.com/leandrokanis/wordcut/issues/3)).

## Contexto

O progresso da tarefa `process` só mudava na troca de etapa: ficava em "baixando 0%" durante
todo o download da faixa e em 35% durante toda a transcrição, que levam minutos numa
pregação longa. A web, a CLI (`--wait`, `task wait`) e a SSE da API leem o mesmo progresso
gravado na tarefa, então a mudança cabe no core.

O yt-dlp baixa uma faixa (`--download-sections`) pelo `ffmpeg`: o `FFmpegFD` do yt-dlp
(`yt_dlp/downloader/external.py`, versão 2026.08.19) só informa bytes quando o download
termina. O `ffmpeg`, com `-progress pipe:1`, informa o tempo de mídia já gravado
(`out_time_us`). O worker do WhisperX já imprime "Progress: N%..." no reconhecimento e no
alinhamento (`print_progress=True`).

## Decisão

- **As portas informam a fração da operação, não a da tarefa.** `download_section`,
  `download_audio_window` e `transcribe` de `ProcessingGateways`, e `Transcriber.transcribe`,
  recebem o parâmetro nomeado `on_progress(fraction)`, de 0 a 1. As portas não conhecem as
  etapas.
- **O pipeline converte a fração na fatia da etapa.** Baixando vai de 0 a 0,30 (faixa de 0 a
  0,28, janela de áudio de 0,28 a 0,30); transcrevendo, de 0,35 a 0,85; sincronizando e
  cortando continuam pontuais. A fração é presa a 0–1 e a etapa guarda o maior valor já
  informado: um valor menor é ignorado, e o progresso nunca passa do início da etapa seguinte.
- **Download pelo yt-dlp.** O adaptador roda o yt-dlp com `--newline --progress
  --progress-template` (bytes baixados sobre o total ou a estimativa) e
  `--downloader-args "ffmpeg_o:-progress pipe:1"` (tempo gravado sobre a duração pedida), e
  lê a saída linha a linha. `--quiet` continua: `--progress` imprime mesmo assim. Quando o
  andamento vem do `ffmpeg` (`out_time_us`), um processo só baixa a faixa inteira, já com
  vídeo e áudio juntos, e o tempo gravado sobre a duração pedida vale de 0 a 1 da faixa; a
  linha de bytes que o yt-dlp imprime ao fim conta como a faixa inteira. Só quando o yt-dlp
  informa o vídeo e o áudio como duas partes por bytes, a primeira ocupa 0–0,9 e a segunda
  0,9–1; uma parte começa quando o andamento da atual volta. Linha que não é progresso é
  ignorada; a falha continua `YouTubeError`, sem o comando nem o caminho dos cookies.
- **Transcrição pelo WhisperX.** O adaptador lê a saída do worker: "Progress: N%" do
  reconhecimento vira 0,9·N/100; "etapa 2/2" vira 0,9; depois dela, "Progress: N%" vira
  0,9 + 0,1·N/100. As linhas continuam indo para a saída da tarefa.
- **Um limitador só.** O gravador de progresso das tarefas (`ProgressRecorder`, em
  `tasks/execution.py`) grava a mesma mensagem no máximo uma vez por segundo e a troca de
  mensagem sempre; o relógio é injetável. Vale para toda tarefa.

## Consequências

- A web, a CLI e a SSE mostram o percentual subindo durante o download e a transcrição, sem
  mudança de contrato.
- Os testes usam dublês da porta e processos falsos (`sys.executable`) no lugar do yt-dlp e do
  worker; nenhum chama o YouTube nem o WhisperX.
- Sem total nem tempo informados, a etapa fica parada no percentual em que está, sem erro.
- O download real da faixa vem de um processo só do `ffmpeg`, que junta vídeo e áudio: o
  andamento da faixa chega ao fim da sua fatia (0,28 da tarefa) antes da janela de áudio,
  que vai de 0,28 a 0,30.
- Mudar as fatias muda só o pipeline; mudar a ferramenta de download ou de transcrição muda
  só o adaptador.
