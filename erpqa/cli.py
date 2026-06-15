from __future__ import annotations

import argparse
from pathlib import Path
import sys

from erpqa.adapters.intake import run_intake
from erpqa.core.compare import compare_contracts
from erpqa.core.context import load_context
from erpqa.core.errors import ErpqaError, UsageError
from erpqa.core.memory import scaffold_project_memory
from erpqa.core.module_scaffold import init_module
from erpqa.core.paths import resolve_project_path
from erpqa.core.policy import scaffold_project_policy
from erpqa.core.scaffold import init_project
from erpqa.core.validation import validate_project
from erpqa.generators.frontend_handoff import generate_frontend_handoff
from erpqa.generators.handoff import generate_handoff
from erpqa.generators.module_contracts import (
    generate_backend_contract,
    generate_frontend_contract,
    generate_procedure_contract,
    generate_screen_contract,
)
from erpqa.generators.sql import generate_sql
from erpqa.reporters.module_report import generate_module_reports
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


def cmd_policy_init(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    init_project(project)
    policy = scaffold_project_policy(project)
    memory, assumptions = scaffold_project_memory(project)
    print(f"Policy initialized or already present: {policy}")
    print(f"Project memory initialized or already present: {memory}")
    print(f"Project assumptions initialized or already present: {assumptions}")
    return 0


def _module_ctx(args: argparse.Namespace):
    project = _existing_project(args.project_path)
    return load_context(project, args.module)


def cmd_module_init(args: argparse.Namespace) -> int:
    project = _existing_project(args.project_path)
    load_context(project, None)
    paths = init_module(project, args.module)
    for path in paths:
        print(f"Initialized or preserved {path}")
    return 0


def cmd_extract_spec(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    path = generate_screen_contract(ctx)
    print(f"Wrote {path}")
    return 0


def cmd_extract_frontend(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    path = generate_frontend_contract(ctx)
    print(f"Wrote {path}")
    return 0


def cmd_extract_backend(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    path = generate_backend_contract(ctx)
    print(f"Wrote {path}")
    return 0


def cmd_extract_procedure(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    path = generate_procedure_contract(ctx)
    print(f"Wrote {path}")
    return 0


def cmd_compare_contract(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    result = compare_contracts(ctx)
    print(f"Comparison complete: {len(result.findings)} findings")
    return 0


def cmd_module_report(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    for path in generate_module_reports(ctx):
        print(f"Wrote {path}")
    return 0


def cmd_module_handoff(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    fix_handoff, codex_prompt = generate_frontend_handoff(ctx)
    print(f"Wrote {fix_handoff}")
    print(f"Wrote {codex_prompt}")
    return 0


def cmd_module_audit(args: argparse.Namespace) -> int:
    ctx = _module_ctx(args)
    stage_status: list[str] = []
    screen_path = generate_screen_contract(ctx)
    stage_status.append(f"extract-spec: {screen_path}")
    frontend_path = generate_frontend_contract(ctx)
    stage_status.append(f"extract-frontend: {frontend_path}")
    backend_path = generate_backend_contract(ctx)
    stage_status.append(f"extract-backend: {backend_path}")
    procedure_path = generate_procedure_contract(ctx)
    stage_status.append(f"extract-procedure: {procedure_path} (validation deferred)")
    result = compare_contracts(ctx)
    stage_status.append(f"compare-contract: {len(result.findings)} findings")
    reports = generate_module_reports(ctx)
    stage_status.append(f"module-report: {len(reports)} reports")
    handoff = generate_frontend_handoff(ctx)
    stage_status.append(f"module-handoff: {handoff[0]}, {handoff[1]}")
    for line in stage_status:
        print(line)
    if ctx.policy.deferred_steps:
        print("Deferred by policy: " + ", ".join(ctx.policy.deferred_steps))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="erpqa", description="ERP QA Kit local CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "init": ("Scaffold qa-context", cmd_init, False),
        "intake": ("Classify target project sources", cmd_intake, False),
        "validate": ("Validate qa-context YAML and SQL safety", cmd_validate, False),
        "generate-sql": ("Generate SELECT-only SQL assertions", cmd_generate_sql, False),
        "report": ("Generate Markdown QA report", cmd_report, False),
        "handoff": ("Generate fix handoff documents", cmd_handoff, False),
        "policy-init": ("Initialize project policy and memory", cmd_policy_init, False),
        "module-init": ("Scaffold a module qa-context", cmd_module_init, True),
        "extract-spec": ("Extract screen spec into screen_contract.yaml", cmd_extract_spec, True),
        "extract-frontend": ("Extract frontend into frontend_contract.yaml", cmd_extract_frontend, True),
        "extract-backend": ("Extract backend into backend_contract.yaml", cmd_extract_backend, True),
        "extract-procedure": ("Extract procedure SQL into procedure_contract.yaml", cmd_extract_procedure, True),
        "compare-contract": ("Compare frontend against source-of-truth contract", cmd_compare_contract, True),
        "module-report": ("Generate module mismatch reports", cmd_module_report, True),
        "module-handoff": ("Generate module frontend fix handoff", cmd_module_handoff, True),
        "module-audit": ("Run module audit end-to-end", cmd_module_audit, True),
    }
    for name, (help_text, func, needs_module) in commands.items():
        sub = subparsers.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("project_path", help="Path to the target ERP project folder")
        if needs_module:
            sub.add_argument("--module", required=True, help="Module name")
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
