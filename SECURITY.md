# Segurança

## Relatar uma vulnerabilidade

Não abra issue pública. Escreva ao mantenedor pelo e-mail do projeto, com a descrição, os
passos para reproduzir e o impacto. A resposta inicial sai em até 7 dias.

## Regras do projeto

- Segredos (chave do LLM, cookies do YouTube) nunca entram no repositório, em log, em saída
  de comando, em resposta da API ou em mensagem de erro (constituição §VI).
- Segredos ficam em `~/.config/wordcut/`, com permissão `600`, montados só para leitura nos
  contêineres.
- O acesso externo é só pelo Cloudflare Tunnel com o Cloudflare Access; as portas
  publicadas escutam em `127.0.0.1` (ADR-0003, ADR-0009).
- Dos membros da equipe se guarda só o e-mail (LGPD).
