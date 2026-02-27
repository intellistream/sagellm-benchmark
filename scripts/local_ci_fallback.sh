#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[local-ci] root: $ROOT_DIR"

echo "[local-ci] step 1/5 install minimal ci deps"
python -m pip install --upgrade pip
python -m pip install pre-commit pytest pytest-cov pytest-asyncio httpx build twine

if [[ -f .pre-commit-config.yaml ]]; then
  PRECOMMIT_RUFF=$(python - <<'PY'
from __future__ import annotations
import re
from pathlib import Path
text = Path('.pre-commit-config.yaml').read_text(encoding='utf-8')
match = re.search(r'repo:\s*https://github.com/astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v([^\s]+)', text)
if not match:
    raise SystemExit('Failed to parse ruff version from .pre-commit-config.yaml')
print(match.group(1))
PY
)
  python -m pip install "ruff==${PRECOMMIT_RUFF}"
fi

echo "[local-ci] step 2/5 pre-commit (all files)"
pre-commit run --all-files

echo "[local-ci] step 3/5 version source guard"
python - <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path('.')
pyproject = root / 'pyproject.toml'
if not pyproject.exists():
    print('No pyproject.toml found, skip version source guard.')
    raise SystemExit(0)

if sys.version_info >= (3, 11):
    import tomllib
else:
    raise RuntimeError('Python 3.11+ is required for tomllib')

data = tomllib.loads(pyproject.read_text(encoding='utf-8'))
project = data.get('project', {})

if 'version' in project:
    raise SystemExit('[FAIL] project.version must not be hardcoded')

dynamic = project.get('dynamic', [])
if 'version' not in dynamic:
    raise SystemExit("[FAIL] [project].dynamic must include 'version'")

attr = (
    data.get('tool', {})
    .get('setuptools', {})
    .get('dynamic', {})
    .get('version', {})
    .get('attr')
)
if not attr or not attr.endswith('._version.__version__'):
    raise SystemExit('[FAIL] [tool.setuptools.dynamic].version.attr must point to <package>._version.__version__')

src = root / 'src'
if not src.exists():
    print('No src/ directory found, skip package file checks.')
    raise SystemExit(0)

package_dirs = [
    path
    for path in src.iterdir()
    if path.is_dir() and (path / '__init__.py').exists() and not path.name.endswith('.egg-info')
]
if not package_dirs:
    print('No package with __init__.py found under src/, skip package file checks.')
    raise SystemExit(0)

errors: list[str] = []
for package_dir in package_dirs:
    package = package_dir.name
    version_file = package_dir / '_version.py'
    init_file = package_dir / '__init__.py'

    if not version_file.exists():
        errors.append(f'[FAIL] missing {version_file.as_posix()}')
        continue

    version_text = version_file.read_text(encoding='utf-8')
    if not re.search(r'^__version__\s*=\s*["\'][^"\']+["\']\s*$', version_text, re.M):
        errors.append(f'[FAIL] {version_file.as_posix()} must define __version__ = "X.Y.Z.N"')

    init_text = init_file.read_text(encoding='utf-8')
    import_patterns = [
        rf'^from\s+{re.escape(package)}\._version\s+import\s+__version__\s*$',
        r'^from\s+\._version\s+import\s+__version__\s*$',
    ]
    if not any(re.search(pattern, init_text, re.M) for pattern in import_patterns):
        errors.append(f'[FAIL] {init_file.as_posix()} must import __version__ from _version.py')

    if re.search(r'^__version__\s*=\s*["\'][^"\']+["\']\s*$', init_text, re.M):
        errors.append(f'[FAIL] {init_file.as_posix()} must not hardcode __version__')

if errors:
    print('\n'.join(errors))
    raise SystemExit(1)

print('[PASS] Version source of truth checks passed.')
PY

echo "[local-ci] step 4/5 pytest + coverage"
pytest tests/ -v --cov=sagellm_benchmark --cov-report=term-missing --cov-report=xml --cov-fail-under=45

echo "[local-ci] step 5/5 package build check"
python -m build
twine check dist/*

echo "[local-ci] all checks passed"
