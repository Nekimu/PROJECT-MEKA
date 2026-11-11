#!/bin/sh
# Elige un intérprete de Python: el del venv del proyecto si existe; si no, el del sistema.
for py in venv/Scripts/python.exe venv/bin/python .venv/Scripts/python.exe .venv/bin/python; do
  [ -x "$py" ] && { PY="$py"; return 0 2>/dev/null || exit 0; }
done
PY=$(command -v python3 || command -v python || command -v py)
