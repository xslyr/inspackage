# Release do inspackage

> **Aviso:** não envie nenhuma tag `v*` antes de concluir a configuração única (Trusted Publisher no PyPI + environment
> `pypi` com required reviewers e regra de tag `v*`). Uma tag enviada antes disso dispara o workflow de publicação sem
> as proteções. Além disso, o merge na `main` é feito pelo usuário na web, e o push de branch ou de tag só acontece com
> aprovação explícita do usuário.

A publicação no PyPI é feita pelo GitHub Actions com **Trusted Publishing** (OIDC): não há token de API no repositório.
O workflow `.github/workflows/publish.yml` roda quando uma tag `v*` é enviada. Ele:

1. (job `build`) confere se o commit da tag está na `main` e se a tag é igual à versão do `pyproject.toml`, e roda
   `poetry check --lock`; se alguma checagem falhar, para aqui;
2. roda `poetry build` e `twine check dist/*`, e envia `dist/` como artifact;
3. (job `publish`, environment `pypi`) publica no PyPI.

O workflow não roda os testes: a tag deve apontar para um commit da `main` com o pipeline verde.

## Configuração única (manual, feita pelo mantenedor)

Nada disto é feito por agentes ou pelo workflow.

1. **PyPI**: na página do projeto `inspackage` → *Manage* → *Publishing* → *Add a new publisher* (GitHub):
   - Owner: `xslyr`
   - Repository name: `inspackage`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
2. **GitHub**: repositório `xslyr/inspackage` → *Settings* → *Environments* → *New environment* → nome `pypi`.
   Recomendado: *Required reviewers* com o seu usuário (cada publicação espera aprovação). Opcional: em
   *Deployment branches and tags*, aceitar apenas tags `v*`.

## Fluxo de release

1. Garanta que a `main` está com o pipeline verde e que a branch de release foi mergeada. O merge na `main` é feito pelo
   usuário na web.
2. Escolha a versão (SemVer, ver política no `CHANGELOG.md`) e grave-a no `pyproject.toml`:
   ```bash
   PYENV_VERSION=system poetry version X.Y.Z
   PYENV_VERSION=system poetry install
   ```
   A versão do pacote vem só do `pyproject.toml`: `inspackage.__version__` lê os metadados do pacote **instalado**.
   Depois de `poetry version`, rode `poetry install` antes do `/qa`; sem isso, o `--version` e o teste de versão
   continuam mostrando a versão antiga.
3. No `CHANGELOG.md`, renomeie `## [Unreleased]` para `## [X.Y.Z] - AAAA-MM-DD`, recrie `## [Unreleased]` vazio e
   atualize os links de comparação no rodapé:
   - `[X.Y.Z]`: `https://github.com/xslyr/inspackage/compare/<base>...vX.Y.Z`, onde `<base>` é a última tag publicada.
     Se ainda não houver tag anterior (como na v0.2.0, já que `v0.1.1` não foi criada), use o commit `90d42e6` como base.
     Para a versão `0.1.1`, o link aponta para `https://pypi.org/project/inspackage/0.1.1/`.
   - `[Unreleased]`: `https://github.com/xslyr/inspackage/compare/vX.Y.Z...HEAD`.
   - Exemplo para a v0.2.0: `[0.2.0]: .../compare/90d42e6...v0.2.0` e `[Unreleased]: .../compare/v0.2.0...HEAD`.
4. Faça o commit (`release: vX.Y.Z`), envie a branch e abra o PR para a `main` **somente com aprovação explícita do
   usuário**. O merge é feito pelo usuário na web.
5. Só depois do merge, com a `main` atualizada e o pipeline verde, crie e envie a tag. Só a tag dispara a publicação.
   O push da tag também exige aprovação explícita do usuário:
   ```bash
   git switch main && git pull --ff-only
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
6. Acompanhe o workflow *Publish* em *Actions*. Se a versão da tag não bater com o `pyproject.toml`, ou se o commit não
   estiver na `main`, o job `build` falha e nada é enviado ao PyPI. O job `publish` espera a aprovação do environment
   `pypi`, se ela estiver configurada.
7. Confira `https://pypi.org/project/inspackage/X.Y.Z/` e, num venv limpo, `pip install inspackage==X.Y.Z` seguido de
   `inspackage --version`.

## Erros comuns

- **Versão já publicada no PyPI não pode ser reenviada.** Se algo der errado depois do upload, corrija e publique uma
  nova versão (patch), em vez de reutilizar o número.
- **Tag errada enviada**: o job `build` barra se a versão não bater ou se o commit não estiver na `main`. Se a tag foi
  criada e o workflow não publicou, apague a tag remota e local antes de repetir o fluxo (apagar tag também exige
  aprovação do usuário).
