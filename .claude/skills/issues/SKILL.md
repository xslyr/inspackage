---
name: issues
description: Fluxo de trabalho com issues do GitHub do inspackage — sincronizar o docs/ROADMAP.md em issues e milestones, listar/triar/responder issues, iniciar o trabalho numa issue ou milestone (cria branch) e finalizar (commits referenciando as issues + push da branch para o usuário fazer o merge na web). Use para "/issues sync", "/issues list", "/issues reply 12", "/issues start 12" ou "/issues start milestone v0.2.0", "/issues finish", ou quando o usuário falar de issues, milestones ou branches de trabalho.
---

# /issues — GitHub issues → branch → push

Repo: `xslyr/inspackage`. Redação e chamadas `gh` são delegadas ao sub-agente **`github-issues`** (haiku). Corpos de issue/comentário vão em arquivos no scratchpad da sessão, nunca no repo.

**Regra de ouro:** criar/editar/comentar/fechar no GitHub e dar push são ações externas. Mostre ao usuário o que será feito e só execute após um "sim" explícito nesta conversa (então chame o agente em modo **APROVADO** com a lista exata). Nunca faça merge, nunca dê push na `main`, nunca force-push.

## `/issues sync` — roadmap → GitHub
1. `github-issues` (RASCUNHO): ler `docs/ROADMAP.md` e issues/milestones existentes; propor labels faltantes (`bug`, `enhancement`, `tests`, `ai`, `release`), milestones por versão (seção 2/Fase 5 do roadmap) e uma issue por item `B*`/`F*` ainda sem issue.
2. Mostre ao usuário um resumo em tabela (ID → título → milestone). Após o "sim", chame em modo APROVADO.
3. Anote o número de cada issue no roadmap (coluna/sufixo `#N`) para o `/improve` achar.

## `/issues list` / `/issues reply N`
- `list`: `github-issues` (RASCUNHO) devolve issues abertas agrupadas por milestone, com as sem milestone destacadas.
- `reply N`: agente lê a issue com comentários e redige resposta; mostre ao usuário; publique só com o "sim".

## `/issues start <N | milestone NOME>`
1. Garanta árvore limpa (`git status`); se houver mudanças, pergunte o que fazer.
2. `git switch main && git pull --ff-only`.
3. Branch:
   - issue única: `fix/<N>-<slug>` (bug) ou `feat/<N>-<slug>` (feature);
   - milestone: `milestone/<versão>` (ex.: `milestone/v0.2.0`), cobrindo todas as issues abertas dela.
4. Liste as issues incluídas e siga para a implementação com a skill **`/improve`**, passando os IDs do roadmap correspondentes.

## Durante o trabalho
- Um commit por issue (ou por passo coerente), mensagem em português no formato:
  `fix(inspection): inclui __init__.py na inspeção (#12)` / `feat(render): exportação HTML (#20)` / `test: fixtures de casos de borda (#5)`.
- Use `Refs #N` no corpo enquanto parcial; `Closes #N` no commit que conclui a issue (fecha automaticamente quando o usuário fizer o merge na `main`).
- Finalize a mensagem com a linha de coautoria exigida pela sessão.
- Rode `/qa` antes de cada commit; não commite com testes falhando.

## `/issues finish`
1. Rode `/qa`; se falhar, pare e reporte.
2. Mostre: branch, commits (`git log main..HEAD --oneline`), issues que serão fechadas, e o comando de push.
3. Após o "sim": `git push -u origin <branch>`.
4. Entregue o link de comparação para o usuário abrir o PR/merge na web:
   `https://github.com/xslyr/inspackage/compare/main...<branch>?expand=1`.
5. Opcional (só se o usuário pedir): `github-issues` (APROVADO) comenta nas issues apontando a branch.
