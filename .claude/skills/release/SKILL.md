---
name: release
description: Prepara uma nova versão do inspackage para o PyPI com Poetry — escolhe a versão SemVer, atualiza pyproject/CHANGELOG, roda /qa, faz build e valida o wheel num venv limpo. Para antes de publicar e entrega os comandos. Use quando o usuário pedir "/release", "preparar versão", "publicar no pypi" ou ao fim de uma fase do roadmap.
---

# /release — preparar versão

1. Confirme que a árvore está limpa (`git status`) e que `/qa` passa. Se não passar, pare e reporte.
2. Leia `CHANGELOG.md` (`Unreleased`) e `git log <última-tag>..HEAD --oneline`; proponha a versão: patch (só correções), minor (features/mudanças de interface em 0.x).
3. Delegue ao sub-agente `release-manager`: `PYENV_VERSION=system poetry version <nova>`, mover `Unreleased` para a nova seção com data de hoje, conferir classifiers/deps/extras.
4. Build e validação:
   ```bash
   export PYENV_VERSION=system
   rm -rf dist && poetry build
   python -m venv "$SCRATCH/relvenv" && "$SCRATCH/relvenv/bin/pip" install dist/*.whl
   "$SCRATCH/relvenv/bin/inspackage" --version
   "$SCRATCH/relvenv/bin/inspackage" --static json | head
   ```
   (`$SCRATCH` = diretório de scratchpad da sessão.) Confira no `unzip -l dist/*.whl` que templates/arquivos de dados estão presentes.
5. **Pare aqui.** Mostre ao usuário: versão, changelog, resultado da validação e os comandos pendentes, por exemplo:
   ```bash
   git commit -am "release: vX.Y.Z" && git tag vX.Y.Z && git push --follow-tags
   ```
   (com Trusted Publishing a tag dispara a publicação; sem ele: `poetry publish`).
   Execute qualquer um deles apenas com aprovação explícita.
