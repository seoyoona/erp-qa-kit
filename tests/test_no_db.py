from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from erpqa.cli import main

from tests.helpers import copy_demo


class NoDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_sql_does_not_open_db_connection(self):
        project = copy_demo(self.tmp_path)
        self.assertEqual(main(["init", str(project)]), 0)
        self.assertEqual(main(["intake", str(project)]), 0)

        def fail_connect(*args, **kwargs):
            raise AssertionError("database connection attempted")

        with mock.patch.object(sqlite3, "connect", fail_connect):
            self.assertEqual(main(["generate-sql", str(project)]), 0)


if __name__ == "__main__":
    unittest.main()

