# Code Quality

## Formatting
- Use `black` for code formatting: `uv run black src/ tests/`
- Line length: 88 (black default)
- Use `isort` for import sorting: `uv run isort src/ tests/`

## Linting
- Use `ruff` for fast linting: `uv run ruff check src/ tests/`
- Fix auto-fixable issues: `uv run ruff check --fix src/ tests/`

## Pythonic Practices
- Use list/dict/set comprehensions over manual loops when readable
- Prefer `pathlib.Path` over `os.path`
- Use f-strings over `.format()` or `%`
- Use `with` statements for resource management
- Prefer `dataclasses` or `NamedTuple` over raw dicts for structured data
- Use `enum.Enum` for fixed sets of values
- Unpack tuples/dicts explicitly — avoid magic indexing

## Anti-patterns to Avoid
- Mutable default arguments (`def f(x=[])`)
- Bare `except:` — always catch specific exceptions
- `import *` — always import explicitly
- Nested functions more than 2 levels deep
- Boolean parameters that change behavior — use separate functions instead
- String concatenation in loops — use `join()` or f-strings
