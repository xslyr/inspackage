---
name: inspect-python-package
description: Entende rapidamente a estrutura de um pacote Python (instalado no venv ou num diretório) usando a CLI inspackage — módulos, classes, funções, API pública e conexões — sem ler arquivo por arquivo. Use quando precisar explorar uma biblioteca desconhecida, descobrir a API de uma dependência, ou mapear um projeto Python antes de modificá-lo.
---

# Entender um pacote Python com inspackage

> Esta skill é também o protótipo da skill que o inspackage vai distribuir para usuários (Fase 4 do roadmap). Mantenha-a atualizada conforme a CLI evolui.

## 1. Garanta a CLI
`inspackage --version` — se não existir: `pipx install inspackage` (ou, neste repo, `PYENV_VERSION=system poetry run inspackage`).

## 2. Escolha o formato pela pergunta
| Objetivo | Comando |
|----------|---------|
| Visão compacta para raciocinar (preferido) | `inspackage <alvo> --format llm` |
| Estrutura completa em texto | `inspackage --static <alvo>` |
| Dados estruturados para filtrar com `jq`/Python | `inspackage <alvo> --format json -o /tmp/pkg.json` (versões antigas: `--save`) |
| Grafo de dependências entre módulos/classes | `inspackage <alvo> --format graph -o /tmp/pkg.graph.json` |
| Relatório de conceitos/conexões via graphify | `inspackage graph <alvo>` (requer `inspackage[graph]`), depois leia `graphify-out/GRAPH_REPORT.md` |
| Mostrar para um humano | `inspackage <alvo> --format html -o pkg.html` |

`<alvo>` = nome importável do pacote (`requests`) ou `--dir caminho/`. Se um flag não existir na versão instalada, use `inspackage --help` e caia para `--static`/`--save`.

## 3. Como ler
1. Comece pela API pública (`__init__.py` / `__all__`) e pelos pontos de entrada.
2. Para pacotes grandes, nunca carregue o JSON inteiro no contexto: filtre (`jq '.nodes[] | select(.name=="core.py")'`).
3. Só abra arquivos-fonte específicos (`path:lineno` da saída) depois de saber onde olhar.
4. Lembre: o inspackage lê o código via AST — não mostra atributos criados dinamicamente nem código gerado em runtime.
