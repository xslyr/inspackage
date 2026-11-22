---
name: release
description: Prepara uma nova versão do inspackage para o PyPI com Poetry — escolhe a versão SemVer, atualiza pyproject/CHANGELOG, roda /qa, faz build e valida o wheel num venv limpo. Para antes de publicar e entrega os comandos. Use quando o usuário pedir "/release", "preparar versão", "publicar no pypi" ou ao fim de uma fase do roadmap.
---

# /release — preparar versão

Publicação: a tag `v*` enviada ao GitHub dispara `.github/workflows/publish.yml` (build, checagem de versão, `twine check` e
publicação por Trusted Publishing). Não existe `poetry publish` no fluxo. Detalhes e passos manuais: `docs/RELEASING.md`.

1. Confirme que a árvore está limpa (`git status`) e que `/qa` passa. Se não passar, pare e reporte.
2. Leia `CHANGELOG.md` (`Unreleased`) e `git log <última-tag>..HEAD --oneline`; proponha a versão pela política do próprio
   CHANGELOG: em 0.x, minor para features e mudanças incompatíveis, patch só para correções. Se não houver tag anterior,
   use o commit `451ca84` (versão 0.1.1) como base do log.
3. Delegue ao sub-agente `release-manager`: `PYENV_VERSION=system poetry version <nova>` seguido de `PYENV_VERSION=system poetry install` (o `__version__` vem dos metadados instalados, então sem reinstalar o `/qa` veria a versão antiga), mover `Unreleased` para a nova seção com data de hoje (e recriar `Unreleased` vazio). Atualize os links do rodapé como descrito em `docs/RELEASING.md`: `[X.Y.Z]` compara a última tag (ou `90d42e6` se não houver tag anterior) com `vX.Y.Z`, e `[Unreleased]` compara `vX.Y.Z...HEAD`. Conferir classifiers/deps/extras.
4. Build e validação:
   ```bash
   export PYENV_VERSION=system
   rm -rf dist && poetry build
   pipx run twine check dist/*
   python -m venv "$SCRATCH/relvenv" && "$SCRATCH/relvenv/bin/pip" install dist/*.whl
   "$SCRATCH/relvenv/bin/inspackage" --version
   "$SCRATCH/relvenv/bin/inspackage" json --format tree | head -5
   ```
   (`$SCRATCH` = diretório de scratchpad da sessão.) Confira no `unzip -l dist/*.whl` que `inspackage/py.typed` está presente e que não há `tests/`.
5. **Pare aqui.** Mostre ao usuário: versão, changelog, resultado da validação e os passos pendentes, nesta ordem:
   ```bash
   # 1. commit da release e push da branch (exige aprovação explícita do usuário)
   git commit -am "release: vX.Y.Z"
   git push origin <branch>
   # 2. abrir o PR para a main (exige aprovação explícita do usuário); o merge é feito pelo usuário na web
   gh pr create --base main --title "release: vX.Y.Z" --body "..."
   # 3. depois do merge, na main atualizada e com o pipeline verde (exige aprovação explícita do usuário)
   git switch main && git pull --ff-only
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z   # dispara publish.yml
   ```
   A tag só é criada depois do merge na `main`; nunca antes. O workflow `publish.yml` também falha se o commit da tag não
   estiver na `main`. Só a tag publica. Se a versão da tag não bater com o `pyproject.toml`, o job `build` falha antes de
   qualquer envio.
   Execute qualquer um desses passos apenas com aprovação explícita do usuário.
