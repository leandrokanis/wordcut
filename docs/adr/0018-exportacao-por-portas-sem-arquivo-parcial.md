# ADR-0018: Exportação do corte por portas, sem arquivo parcial

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md) e a
[ADR-0017](0017-testes-sem-rede-real.md) para o tipo de tarefa `render` (item 1.1.h.1,
[docs/cli.md](../cli.md) §8.7).

## Contexto

Exportar um corte em 9:16 depende de trabalho pesado sobre o vídeo da pregação: `ffprobe`
para a geometria, `ffmpeg` para a energia do áudio, a montagem e a codificação, e OpenCV para
achar o pregador quadro a quadro. Os testes não podem renderizar vídeo real, e o processo
destacado da tarefa monta tudo a partir do ID da tarefa.

Uma exportação dura minutos e pode falhar ou ser interrompida no meio. O arquivo leva o ID da
exportação no nome (`media/cuts/<cut_id>/<render_id>.mp4`), e o ID só existe quando a linha é
gravada. Uma linha sem arquivo, ou um arquivo pela metade, enganaria quem lista ou baixa as
exportações.

A guarda de rede da ADR-0017 não cobre o `ffmpeg` nem o OpenCV: um `render` destacado de
verdade num teste rodaria os dois.

## Decisão

- O pipeline (`wordcut.rendering.pipeline.render_cut`) recebe o mundo externo por uma porta,
  `RenderGateways`: `geometry`, `energy`, `assemble`, `detect` e `render`. A timeline, a
  câmera e as legendas são cálculo puro e ficam no pipeline. `default_gateways()` monta as
  implementações reais (`LocalGateways`), e o tipo de tarefa a chama no processo que roda a
  tarefa.
- O `conftest.py` da raiz tem a fixture autouse `no_real_rendering`, que faz
  `rendering.default_gateways` falhar no processo do pytest. Nenhum teste lança um `render`
  destacado real. O teste que precisa da tarefa `running` usa `harmless_tasks`. O único
  `ffmpeg` real é o de um clipe sintético `lavfi` de 2 s, com a detecção como dublê.
- O pipeline codifica numa pasta de trabalho dentro de `media/cuts/<cut_id>/` e faz
  `os.replace` para o destino só no sucesso. A pasta de trabalho sai em `finally`.
- A tarefa grava a linha em `renders` e move o arquivo para `<render_id>.mp4` na mesma
  transação. Se a transação não for confirmada, o arquivo movido é apagado. A tabela usa
  `AUTOINCREMENT`, então um ID, e o nome de arquivo dele, nunca se repete.
- As opções de exportação são gravadas no corte no gancho `admit`, sob a trava. Uma recusa
  (`busy` e as demais) não grava nada. A estimativa (`--estimate`) não abre mídia: usa a
  timeline com as palavras do banco, sem energia de áudio, a uma taxa nominal de quadros.

## Consequências

- O pipeline, a tarefa e a CLI são testados de ponta a ponta com dublês.
- Uma exportação que falha ou é interrompida (`internal_error`, `interrupted`) não deixa
  linha nem arquivo, nem a pasta de trabalho.
- O arquivo de uma exportação cujo corte é apagado (`sermon suggest`, reprocessamento) fica em
  `media/cuts/<cut_id>/`, porque a linha sai em cascata e ninguém apaga o arquivo. Isso fica
  para o item 1.2.b, que apaga cortes e exportações.
- A estimativa erra o ponto de corte em até meio quadro em relação à exportação real, que usa
  a taxa do vídeo e a energia do áudio.
