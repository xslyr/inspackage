# Release do inspackage

A publicação no PyPI é feita pelo GitHub Actions com **Trusted Publishing** (OIDC): não há token de API no repositório.
O workflow `.github/workflows/publish.yml` roda quando uma tag `v*` é enviada. Ele:

1. (job `build`) confere se a tag é igual à versão do `pyproject.toml`; se não for, para aqui;
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

1. Garanta que a `main` está com o pipeline verde e que a branch de release foi mergeada (o merge é feito pelo usuário na web).
2. Escolha a versão (SemVer, ver política no `CHANGELOG.md`) e grave-a no `pyproject.toml`:
   ```bash
   PYENV_VERSION=system poetry version X.Y.Z
   ```
   A versão do pacote vem só do `pyproject.toml` (`inspackage.__version__` lê os metadados instalados).
3. No `CHANGELOG.md`, renomeie `## [Unreleased]` para `## [X.Y.Z] - AAAA-MM-DD`, recrie `## [Unreleased]` vazio e
   atualize os links de comparação no rodapé.
4. Faça commit (`release: vX.Y.Z`) e mergeie na `main` por PR.
5. Na `main` atualizada, crie e envie a tag. Só a tag dispara a publicação:
   ```bash
   git switch main && git pull --ff-only
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
6. Acompanhe o workflow *Publish* em *Actions*. Se a versão da tag não bater com o `pyproject.toml`, o job `build`
   falha e nada é enviado ao PyPI. O job `publish` espera a aprovação do environment `pypi`, se ela estiver configurada.
7. Confira `https://pypi.org/project/inspackage/X.Y.Z/` e, num venv limpo, `pip install inspackage==X.Y.Z` seguido de
   `inspackage --version`.

## Erros comuns

- **Versão já publicada no PyPI não pode ser reenviada.** Se algo der errado depois do upload, corrija e publique uma
  nova versão (patch), em vez de reutilizar o número.
- **Tag errada enviada**: o job `build` barra se a versão não bater. Se a tag foi criada e o workflow não publicou,
  apague a tag remota e local antes de repetir o fluxo.
