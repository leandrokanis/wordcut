# ADR-0017: Testes sem rede real

**Status**: Aceita · **Data**: 2026-10-26

Complementa a [ADR-0014](0014-processamento-por-portas-e-estado-na-leitura.md) e a
[ADR-0016](0016-sugestao-por-porta-com-falha-na-pregacao.md), que continuam valendo
(portas substituíveis, dublês nos testes).

## Contexto

Os testes trocam `processing.default_gateways` e `suggestion.default_model` por dublês, e as
fixtures `no_real_processing` e `no_real_llm` fazem as reais falharem. As duas proteções só
valem dentro do processo do pytest. Um teste que lança uma tarefa destacada de verdade
(`detached_tasks`) cria um interpretador novo, que monta as fábricas reais. Durante o item
2.1.b.2, um runner destacado de `suggest` com uma chave fictícia chegou ao OpenRouter e
recebeu HTTP 401 (`specs/2.1.b.2-sermon-suggest/qa.md`, rodada 1). Pelo mesmo caminho, um
`process` destacado chegaria ao YouTube.

## Decisão

- Enquanto a variável de ambiente `WORDCUT_FORBID_NETWORK` estiver definida, com qualquer
  valor, `suggestion.default_model` e `processing.default_gateways` recusam com
  `network_error` (saída 6) antes de montar qualquer coisa. `details.forbidden_by` traz o
  nome da variável. A checagem fica em `wordcut.network.refuse_when_forbidden`.
- O `conftest.py` da raiz tem a fixture autouse `no_network`, que define a variável com
  `monkeypatch.setenv`. Todo processo que um teste lança herda o ambiente, inclusive o
  `runner` destacado (`tasks.execution` repassa `os.environ`).
- Os dublês continuam substituindo as fábricas no processo do pytest, então a guarda só age
  onde eles não chegam.
- Um teste lança um `runner` destacado real de `suggest`, com chave e modelo fictícios, e
  exige que a tarefa termine `failed` com o erro da guarda e que o processo saia.

## Consequências

- Uma tarefa destacada real nos testes falha na guarda em vez de chamar o OpenRouter ou o
  YouTube. Um teste que precise da tarefa `running` continua usando `harmless_tasks`.
- A guarda cobre só as duas fábricas. Um teste que monte `OpenRouterModel` ou `YouTube`
  diretamente não passa por ela e precisa do seu próprio dublê de transporte (como o
  `httpx.MockTransport` de `test_openrouter_model.py`).
- Em produção a variável não é definida, e nada muda.
