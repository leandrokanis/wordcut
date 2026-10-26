# ADR-0012: Contrato de saída e erros da CLI

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

Pessoas e agentes operam o Wordcut pela CLI ([docs/cli.md](../cli.md) §3–§5). Um agente só
consegue reagir a um resultado se a saída e os erros forem previsíveis em todo comando:
um único documento JSON no stdout, código de erro estável e código de saída fixo. Se cada
comando montar a própria saída, o contrato se perde a cada comando novo. Os comandos da CLI
anterior continuam no mesmo executável até o item `cli-migration` do roadmap.

## Decisão

- O contrato fica num módulo só, `wordcut_cli.contract`, sobre o `argparse` da biblioteca
  padrão. Todo comando novo se registra por `add_command` e é um handler puro
  `run(args, ctx) -> dict`, com uma função `render(result) -> str` para o texto legível. O
  contrato imprime o resultado: com `--json`, um único documento JSON no stdout; sem ele, o
  texto. `main(argv)` devolve o código de saída.
- `--json` e `--quiet` valem antes ou depois do comando: o parser de cada comando repete as
  duas opções com valor padrão suprimido, para não apagar a escolha feita antes dele.
  `--quiet` chega ao handler pelo contexto (`ctx.quiet`). `--version` mostra a versão da
  distribuição `wordcut-cli`.
- Os erros são `WordcutError(code, message, details)`, do `core` (`wordcut.errors`), com uma
  tabela central código → saída: `internal_error` 1, `invalid_argument` 2, `not_found` 3,
  `busy` 4, regra de negócio 5, falha externa 6 (docs/cli.md §5.1, §5.3). Código fora da
  tabela é recusado ao criar o erro.
- Com `--json`, o erro sai no stdout como `{"error": {"code", "message", "details"?}}`; sem
  ele, o stdout fica vazio e `erro: <message>` vai para o stderr.
- Erro de uso do `argparse` vira `invalid_argument` (saída 2), com `message` em português e
  `details.argument` quando o argumento é identificável.
- Exceção não prevista vira `internal_error` (saída 1) com mensagem genérica; o traceback só
  aparece com `WORDCUT_DEBUG=1`, e sempre no stderr. Ctrl+C sai com 130, sem resultado.
- Os comandos da CLI anterior (`wordcut_cli.legacy`) são registrados no mesmo parser. O
  erro de uso deles segue o contrato, como o de qualquer comando: `invalid_argument`, saída
  2, mensagem em português e o objeto de erro em JSON com `--json`. A saída de sucesso e os
  erros de execução continuam próprios deles, fora do contrato, até o item `cli-migration`.

## Consequências

- Um comando novo herda opções globais, JSON, erros e códigos de saída só por se registrar;
  a mesma tabela de erros serve à API ([ADR-0004](0004-camada-de-servico-no-core.md)).
- Programas decidem pelo `code` e pela saída, nunca pelo texto.
- O `argparse` só informa o erro de uso como texto em inglês; a tradução para português e a
  identificação do argumento dependem dessas mensagens. Uma mensagem que mude numa versão
  do Python cai numa mensagem genérica, ainda com `invalid_argument` e saída 2.
