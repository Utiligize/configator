set dotenv-load

# Print this list
@default:
  just --list
  echo
  echo To add completions in bash, do:
  echo '$ source <(just --completions bash)'
  echo

# Check whether the repo is clean
is-clean:
  @[ -z "$(git status --porcelain)" ]

# Lint the project
lint:
  #!/usr/bin/env bash
  EXIT_STATUS=0
  uv run python -m ruff format {{justfile_directory()}}/src || EXIT_STATUS=$?
  uv run python -m ruff check {{justfile_directory()}}/src || EXIT_STATUS=$?
  cd {{justfile_directory()}}/src && uv run python -m mypy -p configator --config-file {{justfile_directory()}}/pyproject.toml || EXIT_STATUS=$?
  exit $EXIT_STATUS

# Run auto fix for the Ruff linter
lint-auto-fix:
  uv run python -m ruff check --fix {{justfile_directory()}}/src

# Sync dependencies
sync:
  uv sync

# Run test suite
test: sync
  uv run -m pytest

# Rerun failed tests
test-failed: sync
  uv run -m pytest --last-failed
