# Generic ERP QA Troubleshooting

## Missing Quality Artifact

Run `erpqa quality-init <project>` to scaffold missing files, then replace the
generic example values with project evidence.

## Failed Traceability Coverage

Map each high or medium finding to `traceability_matrix.yaml` with a finding ID,
test case, process, screen, and signoff item.

## Failed Impact Coverage

Update `impact_analysis.yaml` so every changed frontend, API, service, stored
procedure, or schema artifact maps to affected tests.

## Open Blocker Or Major Defect

Move confirmed blocker or major defects through fixed, retested, and closed, or
reject them with reviewer and reason.

## Nonzero Cleanup Residual Count

Rerun cleanup for disposable fixture prefixes and record residual count `0` in
`test_data_contract.yaml`.

## Missing Environment Fingerprint

Record build ID, frontend/backend commits, base URL, database alias, browser
device, and account role.

## Flaky Or Quarantined Tests

Apply the flake policy. Quarantined impacted tests fail final QA unless the
policy explicitly allows them with owner, reason, and expiry.

## Package Install Failure

Run `uv build`, install the wheel in a clean virtual environment, and verify
`erpqa --help`.

## CI Coverage Failure

Run `uv run coverage report --fail-under=95`, inspect missing lines, and add
focused tests for release-critical behavior.
