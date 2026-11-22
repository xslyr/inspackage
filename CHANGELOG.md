# Changelog

Todas as mudanças notáveis deste projeto são registradas aqui.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## Política de versão

- **Versões 0.x**: `0.MINOR.0` traz funcionalidades novas e também mudanças incompatíveis (ex.: formato do JSON,
  opções removidas); `0.MINOR.PATCH` traz só correções.
- **A partir de 1.0.0**: SemVer estrito (incompatibilidades só em versão major).
- **JSON exportado é contrato público** (`--format json`, `-o` e `--save`): toda mudança de formato incrementa
  `schema_version` (`SCHEMA_VERSION` em `inspackage/model.py`) e é registrada nas notas de versão abaixo.
- Procedimento de publicação: [docs/RELEASING.md](docs/RELEASING.md).

## [Unreleased]

## [0.2.0] - 2026-11-22

### Added
- Modelo de dados tipado (`inspackage/model.py`: `PackageInfo`, `ModuleInfo`, `ClassInfo`, `FunctionInfo`,
  `VariableInfo`, `ImportInfo`), com `lineno`, docstring (primeira linha), decorators, bases, `is_async`, `kind`
  (method, classmethod, staticmethod, property), imports e `__all__`. O JSON traz `schema_version` (1) e `type`. (#14)
- Erros por arquivo são registrados em `errors` em vez de abortar a inspeção (erro de sintaxe, encoding inválido,
  permissão negada). (#5)
- `--format {tui,tree,json}` e `-o/--output FILE`: saída no terminal ou em arquivo, gravada de forma atômica. Sem
  `--format`, `-o` infere o formato pela extensão (`.json` -> json, `.txt` -> tree). (#15)
- `--include-private`, `--exclude GLOB` (repetível) e `--max-depth N`. (#15)
- Códigos de saída: `0` sucesso, `1` uso inválido, `2` alvo não encontrado, sem módulos ou falha de inspeção. (#15)
- `--verbose` efetivo: caminho resolvido, contagem de módulos e erros no stderr; traceback só em falhas inesperadas. (#11, #15)
- Alvos aceitos: `.`, `./caminho`, caminho absoluto, `~/...`, arquivo `.py`, módulo único (ex.: `typing_extensions`),
  namespace package (sem `__init__.py`) e módulos `frozen` da stdlib. (#3, #14)
- `py.typed` incluído no pacote (PEP 561). (#23)
- CI no GitHub Actions com matriz Python 3.10 a 3.13: `ruff format --check`, `ruff check`, pylint, pytest com
  cobertura mínima de 85% e build com `twine check`. (#24)
- Publicação por tag `v*` via GitHub Actions com Trusted Publishing, sem token. (#25)
- Suíte de testes com fixtures de casos de borda. (#12, #13)

### Changed
- **Quebra de compatibilidade: o JSON gravado por `--save` e por `--format json` mudou de formato.** Agora é o schema
  versionado (`schema_version`, `type`, `modules`, `packages` e demais campos novos). O formato da v0.1.x (`name`,
  `category`, `nodes`) não é mais gravado. Migração: ferramentas que liam o JSON antigo devem ser atualizadas para o
  novo schema; arquivos antigos podem ser regenerados com `inspackage ALVO --format json -o ARQUIVO.json`. (#14, #15)
- `--save` não abre mais a TUI: só grava o JSON. Para gravar e abrir a TUI, use `--format tui --save`. (#10, #15)
- `--save` usa o nome resolvido do pacote ou módulo (`xml.etree` -> `etree.json`; `.` -> nome do diretório), nunca
  `.json`. (#10)
- Alvo não encontrado sai com código `2`. Erros de uso (opção desconhecida, valor inválido) saem com `1`. Mensagens de
  erro vão para o stderr, sem traceback. (#15)
- Ajuda gerada pelo próprio Typer (`-h/--help`), no lugar do texto manual desatualizado. (#11)
- `__init__.py` e `__main__.py` aparecem na árvore. (#6)
- Nomes que começam com `_` ficam ocultos por padrão; use `--include-private` para vê-los. (#6)
- Pacote instalado tem prioridade sobre pasta local de mesmo nome; use `./nome` para forçar a pasta. (#3)
- Diretórios que são symlink não são seguidos. (#5)
- Entradas são ordenadas por nome, então a saída é determinística. (#5)
- `--version` lê a versão dos metadados instalados (`importlib.metadata`). (#23)
- Dependências: `rich` declarado explicitamente; extra `[all]` do `typer` removido (a versão 0.21 não o publica).
  Classifiers para Python 3.10 a 3.13. (#23)
- `--format html`, `md`, `llm` e `graph` são reconhecidos, mas ainda não existem: respondem com erro de uso
  (saída `1`, "não disponível nesta versão"). (#15)
- `-o/--output` grava de forma atômica (arquivo temporário trocado por `os.replace`) e, sem `--format`, infere o
  formato pela extensão. (#15)
- `rich` passa a exigir `>=14.2`, a versão que o `textual` 7.5 suporta. (#23)

### Deprecated
- `--static`: use `--format tree`. Imprime aviso no stderr. (#15)
- `--save`: use `--format json -o <nome>.json`. Imprime aviso no stderr. (#15)

### Fixed
- B01 (#3): `inspackage .` quebrava com `ImportError`; `.` agora é tratado como caminho.
- B02 (#3): módulo único (ex.: `typing_extensions`) varria o diretório `site-packages` inteiro; agora só o arquivo é inspecionado.
- B03 (#3): namespace packages (sem `__init__.py`) davam "não encontrado".
- B04 (#4): `--dir arquivo.py` e diretórios sem módulos quebravam com `KeyError`; agora há mensagem clara.
- B05 (#5): `SyntaxError`, `UnicodeDecodeError` ou `PermissionError` em um arquivo derrubavam a inspeção toda.
- B06 (#6): arquivos como `.pyc`, `.pyi` ou `x.python.txt` eram tratados como módulos Python; agora só `.py` conta.
- B07 (#6): `__init__.py` (onde fica a API pública) e `__main__.py` sumiam por começarem com `_`.
- B08 (#7): o filtro de privados não funcionava e atribuições múltiplas ou em tupla eram ignoradas.
- B09 (#8): `async def` (no topo e em métodos) e classes aninhadas eram ignorados.
- B10 (#7): a classificação era feita por substring do código-fonte (ex.: `super().__init__` virava "constructor");
  agora usa o AST.
- B11 (#7): `params.replace("self", "")` corrompia nomes (`itself` virava `it`); `self` e `cls` agora são removidos pelo AST.
- B12 (#9): propriedades nunca apareciam na árvore.
- B13 (#9): o tema escuro lia `LIGHT_THEME`; agora lê `DARK_THEME`.
- B14 (#10): `--save --dir .` gerava o arquivo `..json`, e o JSON só era gravado depois de fechar a TUI.
- B15 (#11): o help anunciava `-i/--interactive` (inexistente) e omitia `--static`, `--dir` e `--env`; `--verbose` não
  fazia nada.
- B16 (#5): a saída não era determinística (`scandir` sem ordenação) e diretórios symlink eram seguidos, com risco de loop.
- B17 (#23): `rich` era usado sem ser declarado; os classifiers citavam só Python 3.13; a versão estava duplicada em
  `__init__.py`.
- B18 (#12): asserts dentro de `pytest.raises` nunca executavam, havia teste vazio e testes dependiam de pacotes do venv.
- Markup Rich na árvore: anotações como `list[int]` sumiam e um `"[/x]"` no código inspecionado derrubava a
  renderização. Os rótulos agora são escapados. (#9)
- Mensagens de erro que ecoam o alvo digitado não interpretam mais markup: `inspackage '/nonexist[/]'` gerava
  `MarkupError`. (#3, #5)
- Broken pipe (ex.: `inspackage ... | head`) agora sai em silêncio com código `0`, sem mensagem de erro. (#15)
- `RecursionError` e outras exceções inesperadas na coleta de um módulo viram entrada em `errors` em vez de abortar a
  inspeção. (#5)
- Namespace package dividido em vários diretórios é mesclado: subpacotes de mesmo nome são unidos. (#3)
- Nome com `-` (ex.: `typing-extensions`) passa a sugerir o nome com `_` (`typing_extensions`). (#3)
- Todos os `__init__` da classe são exibidos, não só o primeiro. (#9)
- Definições dentro de `if`, `try`, `else` e `finally` no topo do módulo e no corpo de classe são coletadas. (#7)
- Stubs `@overload` são descartados quando há implementação, sem duplicatas na saída. (#7)
- `--env`: o help não expõe mais o caminho da home do usuário. (#11)

## [0.1.1]

Linha de base: versão publicada no PyPI antes deste changelog. Contém a TUI (Textual) de árvore de pacotes e as opções
`--static`, `--save`, `--dir`, `-v/--verbose` e `-e/--env`.

[Unreleased]: https://github.com/xslyr/inspackage/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/xslyr/inspackage/compare/90d42e6...v0.2.0
[0.1.1]: https://pypi.org/project/inspackage/0.1.1/
