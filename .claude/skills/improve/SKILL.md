---
name: improve
description: Orquestra a implementação de um item do docs/ROADMAP.md do inspackage (ex. "/improve B01", "/improve fase 1", "/improve próximo") delegando aos sub-agentes certos (test-engineer, ast-inspector, cli-ux, renderer, ai-context, release-manager, code-reviewer) e validando com /qa. Use sempre que o usuário pedir para avançar no roadmap, corrigir um bug listado ou implementar uma feature planejada.
---

# /improve — orquestrador do roadmap

Argumento: um ID (`B07`), vários (`B07 B08`), uma fase (`fase 1`) ou `próximo` (primeiro item não concluído, na ordem da seção 3 do roadmap).

## 1. Preparar
- Leia `CLAUDE.md` e `docs/ROADMAP.md`; identifique os itens e o estado deles (`git log --oneline -20`, testes `xfail` existentes).
- Localize a issue do GitHub de cada item (sufixo `#N` no roadmap). Se não houver, sugira `/issues sync` antes.
- Nunca trabalhe na `main`: se ainda não estiver numa branch de trabalho, use `/issues start <N | milestone>` para criá-la.
- Registre o plano no task list da sessão (um passo por item/agente).

## 2. Rotear
| Item | Sub-agente principal |
|------|----------------------|
| Fase 0, B18, qualquer fixture/teste | `test-engineer` |
| B02–B12, B16, modelo de dados, Fase 1 | `ast-inspector` |
| B01, B04, B13–B15, Fase 2 | `cli-ux` |
| B12 (lado render), B13, Fase 3 (terminal, TUI, HTML) | `renderer` |
| Fase 4 (llm, graph, graphify, MCP) | `ai-context` |
| B17, Fase 5, versão/CI/PyPI | `release-manager` |
| Issues, milestones, respostas no GitHub | `github-issues` (via `/issues`) |

Modelos: `opus` para ast-inspector, ai-context e code-reviewer (raciocínio pesado); `sonnet` para cli-ux, renderer e test-engineer; `haiku` para release-manager e github-issues. Se um agente barato falhar duas vezes na mesma tarefa, repita com `model: sonnet` na chamada do Agent.

## 3. Executar (test-first)
1. **Teste primeiro**: se o item não tiver teste que o reproduza, chame `test-engineer` com o ID e o comportamento esperado. Confirme que o teste falha (ou está `xfail`).
2. **Implementar**: chame o sub-agente principal com: ID(s), trecho relevante do roadmap, caminho dos testes criados e restrições do `CLAUDE.md`. Itens independentes de agentes diferentes podem rodar em paralelo; itens que tocam o mesmo arquivo, em sequência.
3. Quando a mudança altera o formato do dict/modelo, repasse o novo formato aos agentes de render/CLI/ai-context antes de chamá-los.
4. **Validar**: rode a skill `/qa`. Se falhar, devolva o erro ao sub-agente responsável (máx. 2 voltas; depois reporte ao usuário).
5. **Revisar**: chame `code-reviewer`. Corrija bloqueantes via o sub-agente responsável.

## 4. Fechar
- Remova `xfail` dos testes corrigidos; marque o item como concluído no roadmap (`✅ corrigido em <branch>`).
- Atualize `CHANGELOG.md` (seção `Unreleased`).
- Resuma ao usuário: itens concluídos, arquivos, resultado do /qa, pendências.
- Commit por issue na branch de trabalho, no formato da skill `/issues` (`Closes #N` quando concluir).
- Ao fim do milestone/issue, siga `/issues finish` (push da branch após o "sim" do usuário + link de comparação). O merge na `main` é sempre feito pelo usuário na web.
