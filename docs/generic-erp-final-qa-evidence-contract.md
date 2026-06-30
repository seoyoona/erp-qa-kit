# Generic ERP Final QA Evidence Contract

Final QA is release evidence, not a single test run. A passing packet must
contain these artifacts under `qa-context/quality/`:

- `process_catalog.yaml`: process IDs, module, owner, release scope, ordered
  steps, screen IDs, APIs or stored procedures, tables, and expected state
  changes.
- `traceability_matrix.yaml`: requirement to process to screen to frontend,
  backend, API, database assertion, test case, defect, and signoff links.
- `impact_analysis.yaml`: changed files, applied impact rules, affected
  screens, processes, and tests.
- `test_case_catalog.yaml`: manual, browser, API, DB read-only, and write-UAT
  cases with risk, fixture contract, and expected evidence.
- `test_run_ledger.yaml`: runner, timestamp, environment, account, fixture,
  evidence, result, retry, quarantine, and defect link data.
- `test_data_contract.yaml`: disposable fixture prefixes, cleanup actions, and
  residual count.
- `defect_register.yaml`: defect severity and lifecycle from candidate through
  closed or rejected.
- `environment_fingerprint.yaml`: build, frontend/backend commit, base URL,
  database alias, browser device, and account role.
- `flake_policy.yaml`: retry limit, flaky definition, quarantine requirements,
  and score penalties.

Final QA fails when any required artifact is missing, high or medium findings
lack traceability, impacted tests are not executed, blocker or major defects are
open, cleanup residual count is nonzero, environment fingerprint is absent, or
flaky tests violate policy.
