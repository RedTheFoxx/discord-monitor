# AGENTS.md

## Cursor Cloud specific instructions

### Overview

**discord-monitor** is a single-file Python CLI (`main.py`) that monitors Discord and Vencord installations on Windows, auto-repairs broken Vencord, and can launch Discord at startup. All core functionality is **Windows-only** (`Discord.exe`, `LOCALAPPDATA`, `APPDATA`, Windows Startup folder).

### Tech stack

- **Python >= 3.14** (specified in `pyproject.toml` and `.python-version`)
- **uv** package manager (lockfile: `uv.lock`)
- Dependencies: `click`, `psutil`, `rich`

### Running

```bash
uv run python main.py          # Default status display
uv run python main.py --help   # Show all CLI options
uv run python main.py --monitor # Show Discord process table
```

See `README.md` for the full command reference.

### Important caveats

- **Windows-only**: The actual Discord/Vencord monitoring, repair, and launch features only work on Windows. On Linux, the CLI runs but reports "Discord not found" / "Vencord absent" — this is expected behavior.
- **No automated tests**: The repository has no test suite. Validation is done by running the CLI and checking output.
- **No linter config**: No `ruff`, `flake8`, `mypy`, or similar linter is configured in the project. You can run `uv run python -m py_compile main.py` to check for syntax errors.
- **Python 3.14 is required**: The system Python (3.12) is too old. `uv` handles installing and managing the correct Python version automatically via `uv sync` or `uv run`.
- **Entry point warning**: `uv sync` may emit a warning about skipping entry points because the project has no `build-system`. This is harmless.
