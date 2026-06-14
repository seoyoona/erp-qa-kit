from __future__ import annotations

import argparse
from pathlib import Path
import sys

from erpqa.adapters.intake import run_intake
from erpqa.core.errors import ErpqaError, UsageError
from erpqa.core.paths import resolve_project_path
from erpqa.core.scaffold import init_project
from erpqa.core.validation import validate_project
from erpqa.generators.handoff import generate_handoff
from erpqa.generators.sql import generate_sql
from erpqa.reporters.report import generate_report


def _existing_project(path_arg: str) -> Path:
    return resolve_project_path(path_arg, must_exist=True)


def cmd_init(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    init_project(project)
    print(f"Initialized qa-context at {project / 'qa-context'}")
    return 0


def cmd_intake(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    try:
        count, inventory, manifest = run_intake(project)
    except ValueError as exc:
        raise ErpqaError(str(exc)) from exc
    print(f"Intake complete: {count} source files classified")
    print(f"Wrote {inventory}")
    print(f"Wrote {manifest}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    issues = validate_project(project)
    if issues:
        print("Validation failed:")
        for issue in issues:
            print(f"- {issue.render()}")
        return 1
    print("Validation passed: all qa-context YAML artifacts are valid")
    return 0


def cmd_generate_sql(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    statuses = generate_sql(project)
    print("SQL generation complete:")
    for status in statuses:
        print(f"- {status['rule_id']}: {status['status']} ({status['reason']})")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    report = generate_report(project)
    print(f"Wrote {report}")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    fix_handoff, codex_prompt = generate_handoff(project)
    print(f"Wrote {fix_handoff}")
    print(f"Wrote {codex_prompt}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="erpqa", description="ERP QA Kit local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "init": ("Scaffold qa-context", cmd_init),
        "intake": ("Classify target project sources", cmd_intake),
        "validate": ("Validate qa-context YAML and SQL safety", cmd_validate),
        "generate-sql": ("Generate SELECT-only SQL assertions", cmd_generate_sql),
        "report": ("Generate Markdown QA report", cmd_report),
        "handoff": ("Generate fix handoff documents", cmd_handoff),
    }
    for name, (help_text, func) in commands.items():
        sub = subparsers.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("project_path", help="Path to the target ERP project folder")
        sub.set_defaults(func=func)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except ErpqaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"internal error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
