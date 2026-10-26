# ADR-0015: Erro de uso não repete valor digitado

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0012](0012-contrato-da-cli.md), que continua valendo: o erro de uso do
`argparse` vira `invalid_argument` (saída 2), com `message` em português e
`details.argument` quando o argumento é identificável. Esta ADR muda só o que a mensagem e os
`details` podem conter.

## Contexto

A tradução da ADR-0012 repetia o valor recebido: `Valor inválido para action: '<valor>'`,
`Argumento não reconhecido: <valor>`. Quem digita um segredo no lugar errado, como
`wordcut settings --key <chave> set-key` ou `wordcut settings <chave>`, via a chave no stderr
e no `message` do `--json`, que agentes e logs guardam (item 2.1.a.1, QA da Rodada 1;
[docs/cli.md](../cli.md) §16). A recusa sem eco só nos comandos que leem segredo não basta: o
`argparse` decide qual parser reclama, e o valor pode cair no grupo, no parser raiz ou em
qualquer comando.

## Decisão

- Nenhum erro de uso, em nenhum comando, repete um valor digitado pelo usuário, nem no
  `message` nem nos `details`.
- Escolha inválida (ação ou comando inexistente, opção com `choices`):
  `Valor inválido para <destino>; use um de: a, b, c.`, com
  `details: {"argument": "<destino>", "choices": ["a", "b", "c"]}`.
- Argumento não reconhecido (posicional sobrando, opção que o comando não tem, valor colado
  ao hífen): nunca é repetido, nem como nome de opção, porque um segredo pode ter forma de
  opção (`--sk-or-v1-...`). A mensagem é sempre
  `Argumento não reconhecido; veja wordcut <comando> --help.`, sem `details`; `<comando>`
  vem do parser (o comando e a ação já reconhecidos), nunca do texto digitado.
- O nome de uma opção só aparece na mensagem ou em `details.argument` quando a opção existe
  no parser do comando, como num valor inválido para `--status`, e vem da definição do
  parser (uma abreviação digitada, como `--stat`, aparece como `--status`).
- Valor de tipo inválido (por exemplo, texto num `int`): `Valor inválido para <destino>.`,
  sem o valor.
- Comando que lê segredo do stdin não tem tratamento próprio: a regra geral já recusa
  qualquer argumento sobrando sem repeti-lo, antes de ler o stdin.

## Consequências

- Um segredo digitado no lugar errado não chega à saída, ao `--json` nem a quem guarda o
  stderr, qualquer que seja o parser que o recuse.
- A mensagem perde o valor que ajudaria a achar o erro de digitação, e o argumento não
  reconhecido perde até o nome da opção; a escolha inválida compensa com a lista de opções
  válidas, e o argumento não reconhecido aponta para o `--help` do comando.
- A lista de opções vem do texto do `argparse` (`choose from …`), como os demais padrões da
  ADR-0012. Se a mensagem mudar numa versão do Python, cai no `Valor inválido para
  <destino>.`, ainda sem o valor.
