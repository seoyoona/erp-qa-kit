from __future__ import annotations

import argparse
from pathlib import Path
import sys

from erpqa import __version__
from erpqa.adapters.intake import run_intake
from erpqa.core.compare import compare_contracts
from erpqa.core.context import load_context
from erpqa.core.errors import ErpqaError, UsageError
from erpqa.core.memory import scaffold_project_memory
from erpqa.core.module_scaffold import init_module
from erpqa.core.paths import resolve_project_path, write_yaml
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


def cmd_screen_audit(args: argparse.Namespace) -> int:
    from erpqa.screen.audit import write_screen_audit

    project = _existing_project(args.project_path)
    load_context(project, args.module)
    contract, report = write_screen_audit(
        project, args.module, args.screen, with_labels=getattr(args, "labels", False)
    )
    print(f"Wrote {contract}")
    print(f"Wrote {report}")
    return 0


def cmd_screen_audit_all(args: argparse.Namespace) -> int:
    from erpqa.screen.audit import write_module_screen_audit

    project = _existing_project(args.project_path)
    load_context(project, args.module)
    sy, sm, summary = write_module_screen_audit(
        project, args.module, with_labels=getattr(args, "labels", False)
    )
    print(f"Audited {summary['screens']} screens: CLEAN {summary['clean']} · ISSUES {summary['issues']}")
    print(f"Wrote {sy}")
    print(f"Wrote {sm}")
    return 0


def cmd_isolation_snapshot(args: argparse.Namespace) -> int:
    from erpqa.safety.snapshot import write_isolation_snapshot

    project = _existing_project(args.project_path)
    out = write_isolation_snapshot(project, label=args.label, repos=args.repo or [])
    print(f"Wrote {out}")
    return 0


def cmd_isolation_verify(args: argparse.Namespace) -> int:
    from erpqa.safety.snapshot import write_isolation_comparison

    project = _existing_project(args.project_path)
    out, diff = write_isolation_comparison(project, before_label=args.before, after_label=args.after)
    print(f"Wrote {out}")
    print("Isolation verification passed" if diff["pass"] else "Isolation verification failed")
    return 0 if diff["pass"] else 1


def cmd_trust_score(args: argparse.Namespace) -> int:
    from erpqa.triage.signoff import generate_trust_score

    project = _existing_project(args.project_path)
    yaml_path, report_path, scores = generate_trust_score(project)
    print(f"Wrote {yaml_path}")
    print(f"Wrote {report_path}")
    return 0 if all(score["pass"] for score in scores.values()) else 1


def cmd_quality_init(args: argparse.Namespace) -> int:
    from erpqa.quality.scaffold import scaffold_quality_artifacts

    project = _existing_project(args.project_path)
    paths = scaffold_quality_artifacts(project)
    for path in paths:
        print(f"Initialized or preserved {path}")
    return 0


def cmd_quality_validate(args: argparse.Namespace) -> int:
    from erpqa.quality.validator import validate_quality_packet

    project = _existing_project(args.project_path)
    validation = validate_quality_packet(project)
    if validation["pass"]:
        print("Validation passed: quality evidence packet is complete")
        return 0
    print("Validation failed: quality evidence is incomplete")
    for rel in validation.get("missing_files", []):
        print(f"- missing qa-context/{rel}")
    for reason in validation["fail_reasons"]:
        if not reason.startswith("missing_"):
            print(f"- {reason}")
    print(f"Run `erpqa quality-init {project}` to scaffold required evidence files.")
    return 1


def cmd_quality_impact(args: argparse.Namespace) -> int:
    from erpqa.core.yaml_io import load_yaml
    from erpqa.quality.impact import analyze_change_impact
    from erpqa.quality.policy import load_project_quality_policy

    project = _existing_project(args.project_path)
    qa = project / "qa-context"
    traceability = load_yaml(qa / "quality" / "traceability_matrix.yaml") or {}
    catalog = load_yaml(qa / "quality" / "test_case_catalog.yaml") or {}
    policy = load_project_quality_policy(project)
    impact = analyze_change_impact(args.changed_file or [], traceability, catalog, impact_rules=policy.impact_rules or None)
    out = write_yaml(project, "quality/impact_analysis.yaml", impact)
    print(f"Wrote {out}")
    return 0


def cmd_final_qa_signoff(args: argparse.Namespace) -> int:
    from erpqa.triage.signoff import write_final_qa_signoff

    project = _existing_project(args.project_path)
    out, gate = write_final_qa_signoff(project, module=args.module)
    print(f"Wrote {out}")
    if gate["pass"]:
        print("Final QA signoff passed")
        return 0
    print("Final QA signoff failed: " + ", ".join(gate["fail_reasons"]))
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="erpqa", description="ERP QA Kit local CLI")
    parser.add_argument("--version", action="version", version=f"erpqa {__version__}")
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
        "screen-audit": ("Audit one screen (spec SP fields vs frontend, v0.3)", cmd_screen_audit, True),
        "screen-audit-all": ("Audit every id-coded screen in a module + consolidated summary", cmd_screen_audit_all, True),
    }
    for name, (help_text, func, needs_module) in commands.items():
        sub = subparsers.add_parser(name, help=help_text, description=help_text)
        sub.add_argument("project_path", help="Path to the target ERP project folder")
        if needs_module:
            sub.add_argument("--module", required=True, help="Module name")
        if name == "screen-audit":
            sub.add_argument("--screen", required=True, help="Screen id, e.g. PDT-OSC-001M")
        if name in ("screen-audit", "screen-audit-all"):
            sub.add_argument("--labels", action="store_true",
                             help="Also read screen-layout labels from the spec screenshot via on-device OCR (macOS Vision)")
        sub.set_defaults(func=func)

    iso_snapshot = subparsers.add_parser("isolation-snapshot", help="Write file/git/hash isolation evidence")
    iso_snapshot.add_argument("project_path")
    iso_snapshot.add_argument("--label", required=True)
    iso_snapshot.add_argument("--repo", action="append", default=[])
    iso_snapshot.set_defaults(func=cmd_isolation_snapshot)

    iso_verify = subparsers.add_parser("isolation-verify", help="Compare two isolation snapshots")
    iso_verify.add_argument("project_path")
    iso_verify.add_argument("--before", required=True)
    iso_verify.add_argument("--after", required=True)
    iso_verify.set_defaults(func=cmd_isolation_verify)

    trust_score = subparsers.add_parser("trust-score", help="Score isolation, triage, and final QA evidence")
    trust_score.add_argument("project_path")
    trust_score.set_defaults(func=cmd_trust_score)

    quality_init = subparsers.add_parser("quality-init", help="Scaffold generic ERP quality evidence artifacts")
    quality_init.add_argument("project_path")
    quality_init.set_defaults(func=cmd_quality_init)

    quality_validate = subparsers.add_parser("quality-validate", help="Validate generic ERP quality evidence artifacts")
    quality_validate.add_argument("project_path")
    quality_validate.set_defaults(func=cmd_quality_validate)

    quality_impact = subparsers.add_parser("quality-impact", help="Analyze changed files against traceability evidence")
    quality_impact.add_argument("project_path")
    quality_impact.add_argument("--changed-file", action="append", default=[])
    quality_impact.set_defaults(func=cmd_quality_impact)

    final_signoff = subparsers.add_parser("final-qa-signoff", help="Render final ERP QA signoff packet")
    final_signoff.add_argument("project_path")
    final_signoff.add_argument("--module", required=True)
    final_signoff.set_defaults(func=cmd_final_qa_signoff)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return int(args.func(args))
    except SystemExit as exc:
        return int(exc.code or 0)
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
