"""CLI: migrate Control-M folder/job definitions.

Reads folders and job definitions from a JSON export, replaces job Command
values per a CSV mapping, strips legacy job-name prefixes (and matching text
in descriptions), and writes the result to a new JSON file.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .commands import apply_command_replacements, load_command_replacements
from .job_walker import iter_jobs
from .prefixes import apply_prefix_stripping

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cfn-git-pipeline-migration",
        description=(
            "Migrate Control-M folder/job definitions: replace job commands per a "
            "CSV mapping, then strip legacy job-name prefixes."
        ),
    )
    parser.add_argument(
        "--jobs-json",
        required=True,
        type=Path,
        help="Path to the input Control-M folder/job JSON export.",
    )
    parser.add_argument(
        "--commands-csv",
        required=True,
        type=Path,
        help="CSV file with 'existing_command' and 'replacement_command' columns.",
    )
    parser.add_argument(
        "--output-json",
        required=True,
        type=Path,
        help="Path to write the updated JSON.",
    )
    parser.add_argument(
        "--update-comment",
        required=True,
        help="Comment appended to the Description of every job whose Command is replaced.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    with args.jobs_json.open(encoding="utf-8") as f:
        data = json.load(f)

    jobs = list(iter_jobs(data))
    jobs_read = len(jobs)
    logger.info("Read %d job definition(s) from %s", jobs_read, args.jobs_json)

    replacements = load_command_replacements(args.commands_csv)
    jobs_updated = apply_command_replacements(jobs, replacements, args.update_comment)

    jobs_renamed = apply_prefix_stripping(jobs)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    logger.info("Jobs read: %d", jobs_read)
    logger.info("Jobs updated (command replaced): %d", jobs_updated)
    logger.info("Jobs renamed (prefix stripped): %d", jobs_renamed)
    logger.info("Updated JSON written to %s", args.output_json)

    print(f"Jobs read:                        {jobs_read}")
    print(f"Jobs updated (command replaced):  {jobs_updated}")
    print(f"Jobs renamed (prefix stripped):   {jobs_renamed}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
