---
name: qa
description: Roda a bateria de qualidade do inspackage — ruff (check e format --check), pylint, pytest com cobertura e smoke tests da CLI em casos de borda (pacote por nome, ".", módulo único, namespace, arquivo, sintaxe inválida, --save, html/llm/graph quando existirem). Use após qualquer mudança de código, antes de commit/PR, ou quando o usuário pedir "/qa", "roda os testes", "verifica se está tudo ok".
---

# /qa — verificação completa

Rode a partir da raiz do repo. Use `PYENV_VERSION=system` (o `.python-version` local aponta para um 3.10 inexistente no pyenv).

## 1. Estáticos e testes
```bash
export PYENV_VERSION=system
poetry run ruff format --check inspackage tests
poetry run ruff check inspackage tests
poetry run pylint inspackage
poetry run pytest -q --cov=inspackage --cov-report=term-missing
```
Não aplique `ruff format`/`--fix` automaticamente aqui — só reporte (o usuário ou o agente responsável corrige).

## 2. Smoke da CLI
Rode o script `.claude/skills/qa/smoke.sh`. Ele executa a CLI contra os casos de borda e imprime `OK`/`FAIL` por caso, com o exit code e as últimas linhas de saída quando falha. Casos cujos flags ainda não existem aparecem como `SKIP`.

## 3. Relatório
Responda em tabela curta:

| Etapa | Resultado | Detalhe |
|-------|-----------|---------|

Inclua cobertura total, testes `xfail` restantes (com IDs do roadmap) e, para cada falha, o comando exato para reproduzir. Não declare sucesso se alguma etapa falhou ou foi pulada sem motivo.
