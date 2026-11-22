# inspackage — contexto para agentes

CLI (Typer + Rich + Textual) que inspeciona a estrutura de outro pacote Python via `ast` (sem importar o código alvo).
Publicado no PyPI como `inspackage`; dependências via **Poetry**. Plano de melhorias: `docs/ROADMAP.md` (IDs `B*`/`F*`).

## Mapa do código
- `inspackage/cli.py` — entrypoint `typer_app` (`[project.scripts] inspackage`).
- `inspackage/_inspection.py` — resolve pacote/caminho e gera o `tree_map` (dict) via AST.
- `inspackage/tree.py` — `TreeBuilder` (dict → Rich Tree ou Textual Tree) e `InspackageApp` (TUI).
- `inspackage/_callbacks.py` — help/version, validações, `console`, ícones.
- `inspackage/exception.py` — mensagens de erro.
- `tests/` — pytest (+ `--doctest-modules`).

## Comandos
O `.python-version` pede `3.10`, que não existe no pyenv local: prefixe com `PYENV_VERSION=system` (ou use `.venv/bin/...`).
```bash
PYENV_VERSION=system poetry install
PYENV_VERSION=system poetry run task test   # pytest -v --cov=inspackage
PYENV_VERSION=system poetry run task lint   # pylint
PYENV_VERSION=system poetry run task ruff   # ruff format + check --fix
PYENV_VERSION=system poetry run inspackage --static --dir tests/fixtures/samplepkg
```

## Regras do projeto
- Suportar Python 3.10+ (sem sintaxe 3.11+, ex.: `except*`, `typing.Self`).
- Nunca importar/executar o pacote inspecionado — só `ast` e `importlib.util.find_spec`.
- Testes usam fixtures em `tests/fixtures/`, não pacotes do venv do usuário.
- Todo bug corrigido ganha teste de regressão; toda feature ganha teste.
- O JSON exportado é contrato público: mudanças de formato incrementam `schema_version`.
- Linha máx. 120; ruff + pylint precisam passar.
- Fluxo Git: issue/milestone no GitHub → branch (`fix/<N>-slug`, `feat/<N>-slug` ou `milestone/<versão>`) → commits com `(#N)`/`Closes #N` → push da branch (após o "sim" do usuário) → o **usuário** faz o merge na web. Nunca commitar/push na `main`, nunca merge, nunca force-push. Ver skills `/issues` e `/improve`.
- Não publicar no PyPI nem criar tag sem pedido explícito do usuário.
- Ações no GitHub (criar/comentar/fechar issue, milestone, label) só após confirmação do usuário na conversa.
- `gh` local é 2.4: não tem `gh label`; use `gh api` para labels e milestones.
- Mensagens de commit/PR e docs voltadas ao usuário em português; identificadores de código em inglês.
