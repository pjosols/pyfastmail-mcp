# Language Standards (Python)

## Code Organization
- No file over 200 lines. Split early, not later.
- One class or closely related group of functions per module.
- Use `__init__.py` to define public API for each package.

## Functions & Methods
- Max ~40 lines per function. Extract helpers if longer.
- Single responsibility — one function does one thing.
- Type hints on all signatures. Use `Optional`, `Union` sparingly.
- Google-style docstrings on public functions only.

## Error Handling
- Custom exceptions in a dedicated `exceptions.py`.
- Raise specific, catch specific. No bare `except:`.
- Let unexpected errors propagate — don't swallow them.

## DRY
- Same pattern twice → extract it.
- Shared logic belongs in utils or the client, not in endpoint handlers.

## Style
- Format with `black` (line length 88), sort imports with `isort`, lint with `ruff`.
- No dead code. No TODO comments — either do it or don't.
- f-strings over `.format()`. `pathlib` over `os.path`.
- Comprehensions over manual loops when readable.
- `dataclasses` or `NamedTuple` over raw dicts for structured data.

## Dependencies
- Use `uv` for package management: `uv sync`, `uv run pytest`.
- Dev tools (black, isort, ruff, pytest) go in pyproject.toml `[project.optional-dependencies]` dev group.
