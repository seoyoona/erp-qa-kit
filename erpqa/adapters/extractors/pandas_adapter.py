from __future__ import annotations

from pathlib import Path

from .base import RawExtraction


name = "pandas"
supported_extensions = frozenset({".csv", ".xlsx", ".xlsm"})
tier = "OPTIONAL"


def available() -> bool:
    try:
        import pandas  # noqa: F401
    except Exception:
        return False
    return True


def extract(path: Path) -> RawExtraction:
    if not available():
        return RawExtraction(path.as_posix(), "optional_unavailable", [], "low", ["optional dependency pandas is not installed"], name)
    import pandas as pd

    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
        records = [{"row": int(index) + 2, "values": row.dropna().astype(str).to_dict()} for index, row in frame.iterrows()]
    else:
        sheets = pd.read_excel(path, sheet_name=None)
        records = [
            {"sheet": sheet, "row": int(index) + 2, "values": row.dropna().astype(str).to_dict()}
            for sheet, frame in sheets.items()
            for index, row in frame.iterrows()
        ]
    return RawExtraction(path.as_posix(), "tabular", records, "medium", [], name)

