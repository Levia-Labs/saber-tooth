# saber-tooth

Directives, agents and hooks come from the crepidoma plugin (github.com/Levia-Labs/Crepidoma).

## Project

1. Beat Saber custom-level quality checker and map generator, served as a FastAPI service and CLI.

## Stack

1. Python 3.12, uv, FastAPI, SQLite, pytest, hypothesis, ruff.

## Repo-specific rules

1. Package code lives in `src/saber_tooth`; tests in `tests/`.
2. Project tasks use the `st:` namespace in `tasks/Taskfile.yml`.

## Commands

1. `task --list`; `claude:` and `lint:` come from the Crepidoma submodule.
2. `task st:test` runs the suite.
