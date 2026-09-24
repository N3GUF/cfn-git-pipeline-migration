# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI that migrates Control-M folder/job definition exports (JSON): it replaces job `Command` values per a CSV mapping (appending a comment to the description of every job it updates), then strips legacy job-name prefixes (and matching text in descriptions), writing the result to a new JSON file.

## Commands

```bash
uv sync                     # install/update the venv from pyproject.toml + uv.lock

uv run cfn-git-pipeline-migration \
  --jobs-json data/cfnauth_jobs.json \
  --commands-csv commands.csv \
  --output-json data/cfnauth_jobs_updated.json \
  --update-comment "Updated per PRJTASK0190790 CFN Migration" \
  [--log-level DEBUG]
```

The CSV must have headers `existing_command,replacement_command`. A row is a no-op (no update applied) when `replacement_command` is blank or identical to `existing_command`.

```bash
uv run ruff check .          # lint
uv run ruff format --check . # verify formatting
```

No test suite is configured yet.

## Architecture

Package: `src/cfn_git_pipeline_migration/` (src layout, entry point `cfn-git-pipeline-migration` defined in `pyproject.toml` under `[project.scripts]`, pointing at `cfn_git_pipeline_migration:main` which re-exports `cli.main`).

Processing order matters and is fixed in `cli.main`: **commands are replaced before prefixes are stripped.**

- `job_walker.py` — `iter_jobs(data)` recursively walks the folder JSON and yields `(container, job_key)` for every entry whose `Type` starts with `"Job:"`. `container` is the actual parent dict, so callers mutate/rename jobs in place via `container[job_key]`. This is the only traversal logic; both later stages consume its output rather than re-walking the tree.
- `commands.py` — `load_command_replacements` parses the CSV into an `existing_command -> replacement_command` dict (skipping no-op rows, warning on conflicting duplicate keys). `apply_command_replacements` matches purely on the job's `Command` *text* — there is no job-name/folder lookup — so one CSV row can update many jobs that happen to share a command. Every job it updates also gets the CLI's `--update-comment` value appended to `Description` (on a new line, or as the whole description if none existed).
- `prefixes.py` — `PREFIXES_TO_STRIP` is a hardcoded list of legacy job-name prefixes (e.g. `AUTAPP1_`, `mir01_`, `mir02_`, `sheila_`); there is intentionally no CLI flag to override it. `apply_prefix_stripping` groups jobs by their containing folder and, per folder, precomputes what every job's name would become after stripping — if two or more jobs in the same folder would collide on the same resulting name, **none of them are renamed**; a warning is logged for each and the run continues. Otherwise it renames the job's dict key (via `_rename_key`, which rebuilds the parent dict to preserve key order) and removes the literal prefix substring from `Description` if present.
- `cli.py` — wires the three stages together (commands replaced, *then* prefixes stripped — order matters since collision-skipped jobs keep their prefixed names and thus keep any comment appended in the command step), configures `logging.basicConfig` from `--log-level`, and reports three counts: jobs read, jobs updated (command replaced), jobs renamed (prefix stripped). These are independent counters — a job can be counted in either, both, or neither.

The input JSON shape is a Control-M export: top-level keys are folders (`Type: SimpleFolder`, etc.) containing job entries (`Type: Job:Command`, etc.) as nested dicts; job entries themselves contain further nested dicts (`Rerun`, `When`, `IfBase:...`) that are *not* jobs or folders — `iter_jobs` relies on the `Type` prefix check to avoid descending into those.

Sample data lives in `data/cfnauth_jobs.json` (real Control-M export, not synthetic).
