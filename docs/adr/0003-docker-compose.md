# ADR-0003: Orquestração por Docker Compose

**Status**: Aceita · **Data**: 2026-10-26

## Contexto

A aplicação roda numa máquina pessoal com GPU, junto com outros projetos. Instalar
dependências de sistema (ffmpeg, CUDA, Node) direto no host torna a instalação frágil e
difícil de repetir.

## Decisão

Um `compose.yaml` na raiz orquestra:

- `api`: a API, com acesso à GPU, o volume de dados e os segredos montados só para leitura;
- `web`: a interface compilada, servida por um servidor estático que repassa `/api` para a
  `api`;
- `cli`: a CLI no mesmo ambiente da `api`, sob demanda (`docker compose run --rm cli …`).

Todos compartilham o mesmo volume de dados (`WORDCUT_HOME`), onde ficam o banco, as mídias e
o arquivo da trava. Para desenvolvimento, os projetos Python também rodam no host com
`uv run`.

## Consequências

- A GPU dentro do contêiner exige o NVIDIA Container Toolkit no host.
- A trava (ADR-0006) funciona entre contêineres porque o volume é o mesmo e o kernel é o do
  host.
- O acesso externo continua só pelo Cloudflare Tunnel; as portas publicadas escutam em
  `127.0.0.1`.
