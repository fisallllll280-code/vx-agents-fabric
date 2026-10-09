import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vx_agents_fabric.cli import main, version_pins_from_env
from vx_agents_fabric.registry import default_registry


class CliTests(unittest.TestCase):
    def test_version_pin_env_resolves_exact_agent_version(self):
        registry = default_registry()
        pins = version_pins_from_env(registry, {"VX_AGENT_VERSION_PIN_VX_ENG_TEST": "1.0.0"})
        self.assertEqual(pins["VX-ENG-TEST"], "1.0.0")

    def test_unknown_version_pin_fails_closed(self):
        with self.assertRaises(KeyError):
            version_pins_from_env(default_registry(), {"VX_AGENT_VERSION_PIN_VX_ENG_TEST": "9.9.9"})

    def test_cli_without_provider_adapters_outputs_hold_not_fake_success(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(output):
            code = main(["--goal", "Design a safe research-to-engineering workflow",
                         "--workflow-id", "WF-CLI-TEST"])
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["report"]["status"], "HOLD")
        self.assertFalse(payload["safety_boundary"]["production_authorized"])
        self.assertGreater(len(payload["provider_bindings"]["unconfigured_agent_versions"]), 0)

    def test_cli_writes_complete_report_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "run.json"
            with patch.dict(os.environ, {}, clear=True):
                code = main(["--goal", "Archive an interrupted design safely",
                             "--workflow-id", "WF-CLI-FILE", "--output", str(target)])
            self.assertEqual(code, 2)
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["report"]["workflow_id"], "WF-CLI-FILE")
            self.assertTrue(payload["integrity"]["ledger_valid"])


if __name__ == "__main__":
    unittest.main()
