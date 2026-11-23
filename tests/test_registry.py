"""Tests for agent-registry — fictional data only."""
import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import registry as reg

class TestLifecycle(unittest.TestCase):
    def test_full_lifecycle(self):
        """register -> list -> revoke -> audit shows all events -> report."""
        with tempfile.TemporaryDirectory() as td:
            store = str(Path(td) / "registry-data")
            self.assertEqual(reg.main(["register", "--store", store,
                "--name", "summary-bot", "--owner", "sean",
                "--scope", "Summarize meeting notes",
                "--data-access", "meeting transcripts (read-only)",
                "--model", "vendor-model-x", "--tool", "summary-bot v0.1"]), 0)
            self.assertEqual(reg.main(["register", "--store", store,
                "--name", "demo-writer", "--owner", "sean",
                "--scope", "Draft demo copy", "--data-access", "public demo copy only",
                "--model", "vendor-model-y", "--tool", "demo-writer v0.2"]), 0)
            self.assertEqual(reg.main(["list", "--store", store]), 0)
            self.assertEqual(reg.main(["search", "--store", store, "--query", "summary"]), 0)
            self.assertEqual(reg.main(["revoke", "--store", store,
                "--name", "summary-bot", "--reason", "Cost spike under review"]), 0)
            data = reg.load_registry(store)
            self.assertEqual(data["summary-bot"]["status"], "revoked")
            self.assertEqual(data["summary-bot"]["revoke_reason"], "Cost spike under review")
            self.assertIn("revoked_at", data["summary-bot"])
            events = reg.load_audit(store)
            self.assertEqual([e["event"] for e in events],
                             ["register", "register", "revoke"])
            report = Path(td) / "report.md"
            self.assertEqual(reg.main(["report", "--store", store, "--out", str(report)]), 0)
            text = report.read_text()
            self.assertIn("summary-bot", text); self.assertIn("revoked", text)
            self.assertIn("demo-writer", text)

    def test_negative_paths(self):
        with tempfile.TemporaryDirectory() as td:
            store = str(Path(td) / "registry-data")
            # Revoking an unknown agent fails cleanly (exit 2, no crash)
            self.assertEqual(reg.main(["revoke", "--store", store,
                "--name", "ghost", "--reason", "nope"]), 2)
            # Status change on an unknown agent fails cleanly
            self.assertEqual(reg.main(["status", "--store", store,
                "--name", "ghost", "--new-status", "paused"]), 2)
            # Duplicate register fails cleanly
            self.assertEqual(reg.main(["register", "--store", store,
                "--name", "a", "--owner", "sean", "--scope", "s",
                "--data-access", "none", "--model", "m", "--tool", "t"]), 0)
            self.assertEqual(reg.main(["register", "--store", store,
                "--name", "a", "--owner", "sean", "--scope", "s",
                "--data-access", "none", "--model", "m", "--tool", "t"]), 2)
            # Audit log was only appended to, never rewritten: still 1 event
            self.assertEqual(len(reg.load_audit(store)), 1)

    def test_audit_is_append_only_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            store = str(Path(td) / "registry-data")
            reg.main(["register", "--store", store, "--name", "a", "--owner", "sean",
                      "--scope", "s", "--data-access", "none", "--model", "m", "--tool", "t"])
            _, audit = reg.store_paths(store)
            lines = audit.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["event"], "register")
            self.assertIn("ts", entry)

if __name__ == "__main__":
    unittest.main()
