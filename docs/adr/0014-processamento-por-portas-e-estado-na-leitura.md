# ADR-0014: Processamento da pregação por portas, com o estado conferido na leitura

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0007](0007-tarefas-em-processo-destacado.md) e a
[ADR-0013](0013-trava-herdada-pelo-processo-da-tarefa.md) para o tipo de tarefa `process`
(item 1.1.c.1, [docs/cli.md](../cli.md) §7.4).

## Contexto

Processar a pregação depende de três coisas pesadas e externas: o YouTube (`yt-dlp`), o
WhisperX (GPU) e o `ffmpeg`. Os testes não podem tocar em nenhuma delas, e o processo
destacado da tarefa não recebe objetos Python de quem o lançou: só o ID da tarefa.

A pregação tem estado próprio (`processing`, `processed`, `failed`), além do estado da
tarefa. Sem daemon, ninguém corrige uma pregação `processing` cujo processo morreu. E, sem
`--wait`, o comando volta antes de o filho começar: se só o filho marcasse `processing`, um
`show` logo depois ainda veria a pregação `trimmed`.

## Decisão

- O pipeline (`wordcut.processing.pipeline.process`) recebe o mundo externo por uma porta,
  `ProcessingGateways` (baixar a faixa, baixar a janela de áudio, sincronizar, transcrever,
  medir a duração, cortar). `default_gateways()` monta as implementações reais
  (`LocalGateways`); o tipo de tarefa a chama no processo que roda a tarefa. Os testes
  substituem `default_gateways`, e uma fixture da suíte faz a real falhar se for alcançada.
- `tasks.execution.start` aceita um gancho `admit`, que roda sob a trava antes de a tarefa
  ser gravada: o que ele levanta recusa a tarefa sem criá-la. O serviço usa o gancho para
  revalidar as pré-condições e gravar a pregação `processing` antes do lançamento.
- A tarefa não repete as pré-condições: a trava fica com ela desde o `admit` até o fim, e
  ela só confirma o estado.
  No erro, marca a pregação `failed`; no sucesso, grava palavras, frases e `processed` numa
  única transação.
- Na leitura (`sermon show`, `sermon list`), uma pregação `processing` vira `failed` quando a
  trava não está com ela e nenhuma tarefa dela continua `running` depois da reconciliação de
  tarefas órfãs da ADR-0013.

## Consequências

- O pipeline e o tipo de tarefa são testados de ponta a ponta com dublês; o único `ffmpeg`
  real nos testes é o de um clipe sintético.
- A pregação já aparece `processing` quando o comando sem `--wait` responde.
- Uma pregação nunca fica `processing` para sempre: a primeira leitura depois da morte do
  processo a deixa `failed`, pronta para ser refeita.
- Enquanto outra operação segura a trava, uma pregação `processing` órfã continua aparecendo
  assim se ainda houver tarefa dela `running` em outro host; aceito no MVP, como na ADR-0013.
