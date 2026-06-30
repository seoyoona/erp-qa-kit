# Generic ERP QA Scorecard

## Current Score After Phase

| Area | Score | Evidence |
|---|---:|---|
| Generic product boundary | 9.9 | Boundary test and leakage scan pass across code, tests, public docs, metadata, examples, and release artifacts |
| Architecture | 9.8 | Policy injection, rule-driven impact analysis, strict validators, and negative gate tests pass |
| Test rigor | 9.8 | Full unittest suite, targeted quality tests, release-critical coverage gate at 98%, CLI failure tests, packaging smoke, and release gate tests pass |
| ERP QA maturity | 9.9 | Demo packet validates process, traceability, impact, ledger, defect, data, environment, flake, signoff, and release evidence with 10.0 trust scores |
| CLI usability | 9.8 | Installed CLI exposes documented commands and emits actionable validation failures in the clean-install smoke path |
| Packaging and release | 9.8 | Wheel/sdist build, clean venv pip install, version consistency, and release checklist pass |
| CI and automation | 9.8 | CI workflow includes lint, tests, coverage, build, clean install smoke, leakage scan, security audit, and demo workflow |
| Security and safety | 9.8 | Leakage scan, dependency audit, SQL write-containment tests, no DB write tests, and approval-gated live actions pass |
| Documentation | 9.8 | README, quickstart, evidence contract, runbook, troubleshooting, changelog, release checklist, and scorecard are complete |

## Demo Trust Scores

`examples/pipe-manufacturing-demo/qa-context/trust_score.yaml`:

| Gate | Score | Pass |
|---|---:|---|
| Isolation / safety | 10.0 | yes |
| First-pass triage | 10.0 | yes |
| Final ERP QA readiness | 10.0 | yes |
