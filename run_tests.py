from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


def _load_from_path(path: Path) -> unittest.TestSuite:
    module_name = path.with_suffix("").as_posix().replace("/", ".").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load test file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def main() -> int:
    args = [arg for arg in sys.argv[1:] if arg not in {"-q", "--quiet"}]
    paths = [Path(arg) for arg in args if not arg.startswith("-")]
    if paths:
        suite = unittest.TestSuite(_load_from_path(path) for path in paths)
    else:
        suite = unittest.defaultTestLoader.discover("tests")
    verbosity = 1 if "-q" in sys.argv or "--quiet" in sys.argv else 2
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
