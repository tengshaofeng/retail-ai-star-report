import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import report


class ReportTests(unittest.TestCase):
    def test_rank_growth_ignores_new_repositories_and_sorts(self):
        previous = {
            "a/one": {"stars": 10},
            "b/two": {"stars": 50},
        }
        current = {
            "a/one": {
                "url": "https://github.com/a/one",
                "description": "one",
                "stars": 20,
                "language": "Python",
                "topics": [],
            },
            "b/two": {
                "url": "https://github.com/b/two",
                "description": "two",
                "stars": 55,
                "language": "Python",
                "topics": [],
            },
            "c/new": {
                "url": "https://github.com/c/new",
                "description": "new",
                "stars": 1000,
                "language": "Python",
                "topics": [],
            },
        }
        ranked = report.rank_growth(current, previous)
        self.assertEqual(["a/one", "b/two"], [repo.full_name for repo in ranked])
        self.assertEqual([10, 5], [repo.growth for repo in ranked])

    def test_latest_snapshot_uses_prior_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            (data_dir / "2026-06-01.json").write_text(
                '{"repositories":{"a/one":{"stars":1}}}', encoding="utf-8"
            )
            (data_dir / "2026-07-01.json").write_text(
                '{"repositories":{"a/one":{"stars":2}}}', encoding="utf-8"
            )
            with patch.object(report, "DATA_DIR", data_dir):
                path, repositories = report.latest_snapshot(
                    before=data_dir / "2026-07-01.json"
                )
            self.assertEqual("2026-06-01.json", path.name)
            self.assertEqual(1, repositories["a/one"]["stars"])


if __name__ == "__main__":
    unittest.main()
