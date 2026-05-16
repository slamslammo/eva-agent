from __future__ import annotations

import unittest
from pathlib import Path


class InheritanceDistillationImportBoundaryTests(unittest.TestCase):
    def test_package_does_not_import_framework_or_scenarios(self) -> None:
        root = Path(__file__).resolve().parents[2] / "inheritance_distillation"
        for path in root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("from eva", content, msg=str(path))
            self.assertNotIn("import eva", content, msg=str(path))
            self.assertNotIn("from scenarios", content, msg=str(path))
            self.assertNotIn("import scenarios", content, msg=str(path))


if __name__ == "__main__":
    unittest.main()
