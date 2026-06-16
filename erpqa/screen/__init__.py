"""v0.3 prototype: screen-scoped audit.

Validated against the real pipe-manufacturing ERP (module PDT, screen
PDT-OSC-001M). Unlike the v0.2 module-level extractors, this models ONE screen
at a time and bridges three real sources:

- spec xlsx 화면IO sheet  -> field set from the embedded stored-procedure
  examples (``exec ..._IU @param=``), which is the reliable field source in
  this ERP's design docs (layout/labels live in screenshot images).
- backend module           -> the rosetta mapping between SP params (``iInQty``),
  clean keys (``in_qty``) and DB columns (``INQTY``) from pydantic
  serialization/validation aliases and the service param dicts.
- frontend feature folder  -> zod model field keys + which mutations exist.

It is deliberately conservative: anything inferred carries
``needs_human_confirmation`` and the comparison never rewrites the spec.
"""
