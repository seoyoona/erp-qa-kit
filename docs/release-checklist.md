# Release Checklist

Run these commands before tagging a release:

```bash
uv run ruff check erpqa tests
uv run python -m unittest discover -v
uv run coverage run -m unittest discover
uv run coverage report --fail-under=95
rg -i "customer-specific-leakage-pattern" erpqa tests README.md docs/*.md examples
uv build
ERPQA_RUN_PACKAGING_SMOKE=1 uv run python -m unittest tests.test_packaging_smoke -v
uv run pip-audit
uv run python -m erpqa quality-validate examples/pipe-manufacturing-demo
uv run python -m erpqa final-qa-signoff examples/pipe-manufacturing-demo --module DEMO
git tag v0.3.0
```

The leakage command in CI uses the exact internal pattern. This public checklist
uses a neutral placeholder so the checklist itself remains clean under the
public leakage scan.
