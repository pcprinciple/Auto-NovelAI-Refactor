# Repository Guidelines

## Project Structure & Modules
- `main.py` wires the Gradio Blocks UI, routing user actions to helpers under `src/` and `utils/`.
- `src/` hosts feature-focused modules (e.g., `generate_images`, `director_tools`, `upscale_images`).
- `utils/` contains shared helpers such as component factories, environment handling, and image/file utilities; expect side-effect-heavy logic here.
- `assets/`, `wildcards/`, and `plugins/` store static resources, prompt templates, and optional extensions; keep generated artifacts in `outputs/`.

## Build, Run & Tooling
- `poetry install` — sync the Python 3.10 environment declared in `pyproject.toml`.
- `poetry run python main.py` (or `python main.py`) — launch the full Gradio interface locally.
- `poetry export -f requirements.txt --output requirements.txt` — refresh the `requirements.txt` lock for non-Poetry users when dependencies change.

## Coding Style & Naming
- Follow Black/Isort settings (4-space indentation, 120-char lines) and keep imports grouped with Isort.
- Ruff is configured to enforce `E/W/F` families; run `ruff check .` before committing.
- Prefer descriptive snake_case for functions/variables, PascalCase for classes, and avoid inline lambdas for complex callbacks—move them into `utils/` helpers instead.

## Testing Expectations
- No formal test suite exists; when altering logic, add lightweight verification scripts or Gradio callbacks under `src/` and exercise them via the UI.
- For pure functions, add or update doctest-style examples within module docstrings and run `python -m doctest path/to/module.py`.
- Document manual test steps (input prompts, expected gallery output) in the PR description whenever functionality shifts.

## Commit & PR Workflow
- Match existing history: prefix messages with an emoji surrounded by colons (e.g., `:sparkles:`) followed by a concise Chinese description.
- Keep commits scoped to one change set (UI, tooling, or docs) and include translations where user-facing strings change.
- Pull requests should list the motivation, testing evidence (screenshots for UI tabs), and any configuration requirements (tokens, paths). Link related issues and tag relevant maintainers for review.

## Security & Configuration Notes
- Never hard-code API tokens; rely on the `env` helpers (`utils/environment.py`) and document new keys in `README.md`.
- Respect local file operations: batch tools read/write under `outputs/` — keep destructive actions opt-in and clearly labeled in the UI.
