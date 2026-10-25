"""Validate config-flow fields against UI strings and translations."""
import ast
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"


class FormContractTests(unittest.TestCase):
    def test_translations_match_strings(self):
        strings = json.loads((BASE / "strings.json").read_text())
        translation = json.loads((BASE / "translations" / "en.json").read_text())
        self.assertEqual(strings, translation)

    def test_every_config_field_has_a_label(self):
        strings = json.loads((BASE / "strings.json").read_text())
        fields = {"name", "switch_entity", "power_sensor", "humidity_sensor",
                  "full_power_threshold", "humidity_on_threshold", "humidity_off_threshold",
                  "weekdays", "time_windows"}
        self.assertTrue(fields.issubset(strings["config"]["step"]["user"]["data"]))

    def test_every_options_field_has_a_label(self):
        strings = json.loads((BASE / "strings.json").read_text())
        fields = {"switch_entity", "power_sensor", "humidity_sensor",
                  "full_power_threshold", "humidity_on_threshold", "humidity_off_threshold",
                  "weekdays", "time_windows"}
        self.assertTrue(fields.issubset(strings["options"]["step"]["init"]["data"]))

    def test_error_translation_in_both_flows(self):
        data = json.loads((BASE / "strings.json").read_text())
        for section in ("config", "options"):
            self.assertIn("invalid_schedule", data[section]["error"])

    def test_options_flow_uses_entity_and_dynamic_schedule_fields(self):
        code = (BASE / "config_flow.py").read_text()
        ast.parse(code)
        self.assertIn('entity_field(CONF_SWITCH, data, "switch")', code)
        self.assertIn('entity_field(CONF_POWER, data, "sensor")', code)
        self.assertIn('entity_field(CONF_HUMIDITY, data, "sensor")', code)
        self.assertIn('schedule_fields(data)', code)
        self.assertIn('multiple=True', code)

    def test_listener_registered_before_first_refresh(self):
        code = (BASE / "__init__.py").read_text()
        self.assertLess(
            code.index("entry.add_update_listener(update_listener)"),
            code.index("coordinator.async_config_entry_first_refresh()"),
        )


if __name__ == "__main__":
    unittest.main()
