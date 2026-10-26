# ADR-0004: Camada de serviço única no core

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

O princípio II exige que a CLI e a web façam o mesmo, sem regra de negócio só numa delas,
e que a CLI funcione sem o servidor no ar.

## Decisão

Toda operação do sistema é uma função da camada de serviço em `packages/core`
(`wordcut.service`), que recebe e devolve dados simples e lança `WordcutError` com código
estável. A CLI e a API são adaptadores finos: traduzem argumentos ou requisições em chamadas
de serviço e o resultado em saída. A CLI chama o serviço direto, sem passar pela API.

## Consequências

- Um teste de serviço cobre a CLI e a API ao mesmo tempo.
- Os códigos de erro (`docs/cli.md` §5) valem também para a API.
