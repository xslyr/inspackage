#!/usr/bin/env bash
# Smoke tests da CLI do inspackage contra casos de borda.
# Uso: bash .claude/skills/qa/smoke.sh   (a partir da raiz do repo)
set -u
export PYENV_VERSION=system
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CLI="$ROOT/.venv/bin/inspackage"
[ -x "$CLI" ] || CLI="poetry -C $ROOT run inspackage"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FIX="$ROOT/tests/fixtures"
HELP="$($CLI --help 2>&1)"
pass=0; fail=0; skip=0

has_flag() { grep -q -- "$1" <<<"$HELP"; }

run() { # nome, comando...
  local name="$1"; shift
  local out code
  out="$(cd "$WORK" && timeout 60 "$@" 2>&1)"; code=$?
  if [ $code -eq 0 ] && ! grep -q "Traceback" <<<"$out"; then
    echo "OK    $name"; pass=$((pass+1))
  else
    echo "FAIL  $name (exit $code)"; tail -n 4 <<<"$out" | sed 's/^/      /'; fail=$((fail+1))
  fi
}

expect_error() { # nome, comando... -> deve sair != 0 sem traceback
  local name="$1"; shift
  local out code
  out="$(cd "$WORK" && timeout 60 "$@" 2>&1)"; code=$?
  if [ $code -ne 0 ] && ! grep -q "Traceback" <<<"$out"; then
    echo "OK    $name"; pass=$((pass+1))
  else
    echo "FAIL  $name (exit $code, esperado erro amigável)"; tail -n 4 <<<"$out" | sed 's/^/      /'; fail=$((fail+1))
  fi
}

skip() { echo "SKIP  $1"; skip=$((skip+1)); }

run "help"                       $CLI --help
run "version"                    $CLI --version
run "pacote por nome (json)"     $CLI --static json
run "--dir do próprio projeto"   $CLI --static --dir "$ROOT/inspackage"
run "'.' (exemplo do README)"    bash -c "cd '$ROOT/inspackage' && $CLI --static ."
run "módulo único (não varrer site-packages)" bash -c "$CLI --static typing_extensions | head -1 | grep -qv site-packages"
run "--dir apontando para arquivo" $CLI --static --dir "$ROOT/inspackage/cli.py"
run "--save grava json"          bash -c "$CLI --static --save --dir '$ROOT/inspackage' >/dev/null && ls *.json"
expect_error "pacote inexistente" $CLI --static pacote_que_nao_existe_xyz

if [ -d "$FIX" ]; then
  run "fixture samplepkg"        $CLI --static --dir "$FIX/samplepkg"
  [ -d "$FIX/nspkg" ] && run "namespace package" bash -c "PYTHONPATH='$FIX' $CLI --static nspkg"
else
  skip "fixtures (tests/fixtures ausente — Fase 0)"
fi

# formatos aceitos = registro FORMATS do pacote (fallback: linha "--format" do help)
FORMATS="$("$ROOT/.venv/bin/python" -c "from inspackage.render import FORMATS; print(' '.join(FORMATS))" 2>/dev/null)" || FORMATS=""
if [ -z "$FORMATS" ]; then
  FORMATS="$(grep -o 'tui[^.]*' <<<"$($CLI --help 2>&1 | tr '\n' ' ' | grep -o -- '--format .*' )" | head -1)"
fi
for fmt in html llm graph json; do
  if ! has_flag "--format"; then
    skip "--format $fmt (flag ainda não existe)"
  elif ! grep -qw -- "$fmt" <<<"$FORMATS"; then
    expect_error "--format $fmt (ainda indisponível: erro de uso amigável)" $CLI --dir "$ROOT/inspackage" --format "$fmt" -o "$WORK/out.$fmt"
  else
    run "--format $fmt" $CLI --dir "$ROOT/inspackage" --format "$fmt" -o "$WORK/out.$fmt"
  fi
done

echo "---"; echo "pass=$pass fail=$fail skip=$skip"
[ $fail -eq 0 ]
