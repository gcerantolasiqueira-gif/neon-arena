# Neon Arena Beta v1.0 - Publicação

Este projeto está preparado para um beta público sem dinheiro real.

## O que esta versão permite

- Criar conta com apelido, usuário e senha.
- Jogar Air Hockey online por sala privada ou matchmaking.
- Jogar mesas grátis ou com Moedas Neon fictícias.
- Usar chat global da arena.
- Ver histórico, carteira fictícia e ranking.

## Aviso importante

As Moedas Neon desta fase são fictícias. Não existe depósito, saque, prêmio financeiro ou aposta real nesta versão.

## Publicação recomendada no Render

1. Crie uma conta em `https://render.com`.
2. Coloque a pasta `neon-air-hockey` em um repositório no GitHub.
3. No Render, clique em `New` e depois em `Blueprint`.
4. Escolha o repositório da Neon Arena.
5. O Render deve ler o arquivo `render.yaml`.
6. Confirme a criação do serviço.
7. Aguarde o build terminar.
8. Abra a URL pública gerada pelo Render.

## Variáveis importantes

- `NEON_ENV=production`
- `NEON_DB_PATH=/var/data/neon_arena.db`
- `NEON_ALLOWED_HOSTS=*`

Para domínio próprio, troque `NEON_ALLOWED_HOSTS=*` pelo domínio real, por exemplo:

```text
NEON_ALLOWED_HOSTS=neonarena.com.br,www.neonarena.com.br
```

## Comando local

Dentro da pasta `backend`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Antes de virar aposta real

Ainda será necessário criar:

- Termos de uso completos.
- Política de privacidade.
- Sistema antifraude.
- Auditoria de partidas e carteira.
- Banco PostgreSQL ou estrutura equivalente.
- Painel administrativo.
- Análise jurídica e regulatória.
- Sistema de pagamento, KYC e saque somente se for legalmente permitido.

