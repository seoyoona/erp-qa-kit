# Generic ERP QA Operator Runbook

Run the deterministic offline workflow first:

```bash
uv run python -m erpqa init <project>
uv run python -m erpqa quality-init <project>
uv run python -m erpqa isolation-snapshot <project> --label before
uv run python -m erpqa screen-audit-all <project> --module <MODULE>
uv run python -m erpqa quality-impact <project> --changed-file <PATH>
uv run python -m erpqa quality-validate <project>
uv run python -m erpqa trust-score <project>
uv run python -m erpqa final-qa-signoff <project> --module <MODULE>
```

Only collect browser, API, SQL, or write-UAT evidence after explicit human
approval. Write-UAT fixtures must be disposable, must use a unique prefix, and
must end with residual count `0`.

If `quality-validate` fails, inspect the missing artifact path or failed field,
fill the evidence, and rerun the same command. Do not bypass the final signoff
gate for release decisions.
