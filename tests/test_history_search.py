import tempfile
import unittest
from pathlib import Path
from veilbreaker.core import VeilbreakerStore


class HistorySearchTests(unittest.TestCase):
    def test_search_paging_and_preceding_run_across_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            store = VeilbreakerStore(Path(folder) / "history.db")
            try:
                for i in range(405):
                    store.db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (f"run-{i:04}", "2026-10-02T12:00:00Z", "Roof" if i in (0,404) else "Office", "field_validation", "{}", "{}", "", "100%_literal" if i == 0 else "routine"))
                store.db.commit()
                first, count = store.search_runs()
                second, _ = store.search_runs(offset=200)
                last, _ = store.search_runs(offset=400)
                self.assertEqual(count, 405)
                self.assertEqual([len(first), len(second), len(last)], [200,200,5])
                self.assertEqual(len({r["run_id"] for r in first+second+last}), 405)
                rows, count = store.search_runs("%_")
                self.assertEqual(count, 1)
                self.assertEqual(rows[0]["run_id"], "run-0000")
                self.assertEqual(store.search_runs("' OR 1=1 --")[1], 0)
                self.assertEqual(store.search_runs("roof")[1], 2)
                self.assertEqual(store.preceding_run(first[0])["run_id"], "run-0000")
                self.assertIsNone(store.preceding_run(rows[0]))
            finally:
                store.close()
