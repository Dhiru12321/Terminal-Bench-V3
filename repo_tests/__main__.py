from __future__ import annotations

import shutil
import os
import sys
import unittest
from pathlib import Path


def main() -> int:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    repo_root = Path(__file__).resolve().parents[1]
    for cache_dir in (repo_root / "__pycache__", repo_root / "scripts" / "__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
