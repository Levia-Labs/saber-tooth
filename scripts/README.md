# scripts

Standalone helper scripts run through the task runner.

1. `readme_check.py`: checks that every tracked project folder has a README.md. Run `task st:readme-check` to list missing folders (exit 1 if any) or `task st:readme-check -- --list` to list every folder that needs one. Tested by `tests/test_readme_check.py`.

Tasks are defined in [tasks/Taskfile.yml](../tasks/README.md).
