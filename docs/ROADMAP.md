# Roadmap de melhorias — inspackage

Estado de partida: `v0.1.1` (publicado no PyPI), Python >=3.10, Poetry, Typer + Textual + Rich.
Diagnóstico feito em 2026-11-22 rodando a CLI contra casos de borda.

Cada item tem um ID (`B*` bug, `F*` feature) e a issue do GitHub correspondente (`#N`). Use `/issues start <N | milestone v0.2.0>` para abrir a branch e `/improve <ID>` para implementar.
Milestones: [v0.2.0](https://github.com/xslyr/inspackage/milestone/1) · [v0.3.0](https://github.com/xslyr/inspackage/milestone/2) · [v0.4.0](https://github.com/xslyr/inspackage/milestone/3).

---

## 1. Bugs confirmados / encontrados

| ID | Onde | Problema | Confirmado |
|----|------|----------|-----------|
| B01 [#3](https://github.com/xslyr/inspackage/issues/3) ✅ | `cli.py:41` / `_inspection.py:27` | `inspackage .` (exemplo do README) quebra: `.` é tratado como nome de pacote → `ImportError` com traceback. | ✅ rodado |
| B02 [#3](https://github.com/xslyr/inspackage/issues/3) ✅ | `_inspection.py:33` | Pacote de módulo único (ex.: `typing_extensions`, `six`) → `dirname(spec.origin)` = `site-packages` → varre o venv inteiro. | ✅ rodado |
| B03 [#3](https://github.com/xslyr/inspackage/issues/3) ✅ | `_inspection.py:29` | Namespace packages (sem `__init__.py`) dão "not found" porque `spec.origin` é `None`; deveria usar `submodule_search_locations`. | ✅ rodado |
| B04 [#4](https://github.com/xslyr/inspackage/issues/4) ✅ | `tree.py:60` | `--dir arquivo.py` → `KeyError: 'nodes'`; mapa vazio (`{}`) → `KeyError: 'name'`. | ✅ rodado |
| B05 [#5](https://github.com/xslyr/inspackage/issues/5) ✅ | `_inspection.py:42-43` | `SyntaxError`/`UnicodeDecodeError` em um arquivo derruba a inspeção toda; `PermissionError` no `scandir` idem. | ✅ rodado (SyntaxError) |
| B06 [#6](https://github.com/xslyr/inspackage/issues/6) ✅ | `_inspection.py:41` | `".py" in name` aceita `.pyc`, `.pyi`, `x.python.txt`. | leitura |
| B07 [#6](https://github.com/xslyr/inspackage/issues/6) ✅ | `_inspection.py:41,49` | Ignora tudo que começa com `_` → some `__init__.py` (onde fica a API pública!), `__main__.py`, `_private/`. | leitura |
| B08 [#7](https://github.com/xslyr/inspackage/issues/7) ✅ | `_inspection.py:66,70,86,89` | `str(node.targets[0])` é o repr do nó AST → filtro de privados nunca funciona; atribuições múltiplas/tuplas ignoradas. | leitura |
| B09 [#8](https://github.com/xslyr/inspackage/issues/8) ✅ | `_inspection.py:73,91` | `AsyncFunctionDef` ignorado (top-level e métodos). Classes aninhadas ignoradas. | leitura |
| B10 [#7](https://github.com/xslyr/inspackage/issues/7) ✅ | `_inspection.py:92-105` | Classificação por substring do código-fonte: qualquer método que chame `super().__init__` vira "constructor"; método com `def _x` interno some; `@property` detectado por texto. Usar `node.name` e `node.decorator_list`. | leitura |
| B11 [#7](https://github.com/xslyr/inspackage/issues/7) ✅ | `_inspection.py:100-101` | `params.replace("self", "")` corrompe nomes (`itself` → `it`, `cls_name` → `_name`). Remover o 1º argumento via AST. | leitura |
| B12 [#9](https://github.com/xslyr/inspackage/issues/9) ✅ | `_inspection.py:95` vs `tree.py:175` | Grava em `"properties"` mas o renderizador procura `"property"` → propriedades nunca aparecem. | leitura |
| B13 [#9](https://github.com/xslyr/inspackage/issues/9) ✅ | `tree.py:207` | `dark_theme` lê a variável `LIGHT_THEME`. | leitura |
| B14 [#10](https://github.com/xslyr/inspackage/issues/10) ✅ | `cli.py:72` | `--save --dir .` relativo → arquivo `..json`; e `--save` só grava *depois* de fechar o TUI. | leitura |
| B15 [#11](https://github.com/xslyr/inspackage/issues/11) ✅ | `_callbacks.py:9-18` | Help manual desatualizado: anuncia `-i/--interactive` (não existe) e omite `--static`, `--dir`, `--env`. `--verbose` não faz nada. | leitura |
| B16 [#5](https://github.com/xslyr/inspackage/issues/5) ✅ | `_inspection.py:51` | `scandir` sem ordenação → saída não determinística; segue symlinks (risco de loop). | leitura |
| B17 [#23](https://github.com/xslyr/inspackage/issues/23) | `pyproject.toml` | `rich` usado diretamente mas não declarado; classifiers só citam 3.13; versão duplicada em `__init__.py` (usar `importlib.metadata`). `.python-version`=3.10 não instalado no pyenv local. | leitura |
| B18 [#12](https://github.com/xslyr/inspackage/issues/12) ✅ | `tests/` | Asserts dentro de `pytest.raises` nunca executam; teste vazio (`...`); testes dependem de pacotes do venv (`rich`, `dotenv`). | leitura |

Legenda: ✅ corrigido na branch `milestone/v0.2.0`.

## 2. Fases

### Fase 0 — Rede de segurança (testes primeiro)
_Issue: #13 — milestone v0.2.0 — ✅ concluída_
- Criar `tests/fixtures/samplepkg/` cobrindo: `__init__.py` com reexports, módulo com async, property, classmethod/staticmethod, classe aninhada, herança, constantes anotadas, privados, arquivo com erro de sintaxe, subpacote, namespace package, módulo único.
- Testes de caracterização do comportamento atual (marcar com `xfail` os bugs B01–B18).
- `conftest.py` com fixture `run_cli` (CliRunner) e snapshot simples de JSON.
- Meta: cobertura ≥ 85% em `inspackage/`.

### Fase 1 — Núcleo de inspeção correto
_Issue: #14 — milestone v0.2.0 — ✅ concluída (exposta pela CLI na #15)_
- Novo modelo de dados tipado (`inspackage/model.py`, dataclasses): `PackageInfo`, `ModuleInfo`, `ClassInfo`, `FunctionInfo`, `VariableInfo` com `lineno`, `docstring` (1ª linha), `decorators`, `bases`, `is_async`, `kind` (method/classmethod/staticmethod/property), `imports`, `__all__`.
- Resolver origem: nome → path (pacote, módulo único, namespace) e path → módulo; aceitar `.`.
- Coletar erros por arquivo em `ModuleInfo.errors` em vez de abortar.
- Opções: `--include-private`, `--exclude GLOB`, `--max-depth`.
- `to_dict()` estável com `schema_version` (o JSON vira contrato público).
- Corrige B02–B12, B16.

### Fase 2 — CLI
_Issue: #15 — milestone v0.2.0 — ✅ concluída (`--save` grava o JSON novo: quebra intencional, ver comentário na #15)_
- Interface compatível: `inspackage [ALVO] [--dir PATH] --format {tui,tree,json,html,md,llm,graph} [-o ARQ]`.
- `--static` → alias de `--format tree`; `--save` → alias de `--format json -o <nome>.json` (manter, com aviso de depreciação).
- Usar help nativo do Typer (remover template manual) — corrige B15.
- Erros amigáveis sem traceback e códigos de saída: 0 ok, 1 erro de uso, 2 alvo não encontrado.
- Corrige B01, B04, B13, B14.

### Fase 3 — Visualização
_Issues: #16 (Rich), #17 (TUI), #18 (HTML) — milestone v0.3.0_
- **Terminal (Rich)**: cores por categoria, assinaturas com `rich.syntax`, docstring resumida, nº de linha, painel de estatísticas (módulos/classes/funções), `--no-icons`/`--no-color` para terminais simples.
- **TUI (Textual)**: painel de detalhes ao lado da árvore (docstring + código do nó), busca `/`, expandir/colapsar tudo, exportar a partir do TUI.
- **HTML**: arquivo único autocontido (CSS/JS inline, sem CDN), árvore com `<details>`, busca, tema claro/escuro, links por âncora. Template em `inspackage/render/templates/` incluído no wheel.
- Arquitetura: `inspackage/render/{rich_tree,tui,html,markdown,json,graph}.py`, todos consumindo o mesmo modelo.

### Fase 4 — Entendimento por agentes de IA
_Issues: #19 (llm), #20 (graph), #21 (graphify), #22 (MCP) — milestone v0.4.0_
- `--format llm`: Markdown compacto e determinístico pensado para contexto de LLM — mapa de módulos, API pública (`__all__`/`__init__`), assinaturas + 1ª linha de docstring, grafo de imports internos, pontos de entrada (`[project.scripts]`, `__main__`). Opção `--budget N` (tokens aprox.) que poda os detalhes menos importantes.
- `--format graph`: JSON node-link (nós: package/module/class/function; arestas: `contains`, `imports`, `inherits`, `calls` opcional) — compatível com NetworkX `node_link_data`.
- Integração com **graphify** (`pip install graphifyy`, CLI `graphify`): extra opcional `inspackage[graph]`; subcomando `inspackage graph ALVO` que (a) exporta o grafo no formato que o graphify consome ou (b) chama `graphify` se instalado e aponta para `graphify-out/GRAPH_REPORT.md`. **Validar o schema real do `graph.json` do graphify antes de codar** (não presumir).
- Opcional: servidor MCP (`inspackage mcp`) com ferramentas `inspect_package`, `get_symbol`, `find_usages`.
- Distribuir uma skill (`inspect-python-package`) que ensina agentes a usar a CLI.

### Fase 5 — Release
_Issues: #23 (versão/deps), #24 (CI), #25 (Trusted Publishing), #26 (CHANGELOG) — milestone v0.2.0_
- Versão única via `importlib.metadata.version("inspackage")`.
- CI: matriz Python 3.10–3.13; `ruff format --check` (CI não deve reformatar); `pytest --cov --cov-fail-under=85`.
- `CHANGELOG.md`, classifiers corretos, `rich` como dependência explícita, `py.typed`.
- Publicação via GitHub Actions + Trusted Publishing (PyPI) em tags `v*`.
- Versão alvo: `0.2.0` (fases 0–2), `0.3.0` (fase 3), `0.4.0` (fase 4).

## 3. Ordem sugerida
`F0 → B01..B18 (Fase 1/2) → Fase 3 (HTML primeiro) → Fase 4 (llm → graph → graphify) → Fase 5` — release ao fim de cada fase.
