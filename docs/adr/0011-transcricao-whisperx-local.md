# ADR-0011: Transcrição com WhisperX na GPU local

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

O corte palavra a palavra exige tempo por palavra; enviar o áudio para fora custaria e
exporia o conteúdo.

## Decisão

A transcrição usa WhisperX na GPU da máquina, dentro do contêiner da `api`/`cli`, com o
modelo configurável. Só a faixa da pregação é transcrita.

## Consequências

- A imagem com CUDA é grande; ela é construída uma vez e reaproveitada.
- Sem GPU disponível no contêiner, a transcrição falha com erro claro.
