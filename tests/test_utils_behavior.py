"""Test persisted date handling and entity slug creation."""
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"


class UtilsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
        package.__path__ = [str(BASE)]
        dt = sys.modules.setdefault("homeassistant.util.dt", types.ModuleType("homeassistant.util.dt"))
        dt.parse_datetime = datetime.fromisoformat
        util = sys.modules.setdefault("homeassistant.util", types.ModuleType("homeassistant.util"))
        util.dt = dt
        spec = importlib.util.spec_from_file_location("dehumidifier_plug.real_utils_test", BASE / "utils.py")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_slug_normalizes_diacritics(self):
        self.assertEqual(self.module.slugify("Suíte - WC 1º"), "suite_wc_1o")

    def test_slug_collapses_whitespace_and_hyphens(self):
        self.assertEqual(self.module.slugify(" Living  -   Room "), "living_room")

    def test_none_and_empty_datetime(self):
        for value in (None, "", "  ", 1, {}, []):
            with self.subTest(value=value):
                self.assertIsNone(self.module._safe_parse_dt(value))

    def test_aware_datetime_preserved(self):
        dt = datetime(2026, 10, 25, 12, tzinfo=timezone(timedelta(hours=1)))
        self.assertEqual(self.module._safe_parse_dt(dt), dt)

    def test_naive_datetime_assumes_utc(self):
        dt = datetime(2026, 10, 25, 12)
        self.assertEqual(self.module._safe_parse_dt(dt).tzinfo, timezone.utc)

    def test_iso_datetime_with_offset(self):
        result = self.module._safe_parse_dt("2026-10-25T12:00:00+01:00")
        self.assertEqual(result.utcoffset(), timedelta(hours=1))

    def test_fallback_to_standard_iso_parser(self):
        with patch.object(self.module.dt_util, "parse_datetime", return_value=None):
            result = self.module._safe_parse_dt("2026-10-25T12:00:00")
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_invalid_string_returns_none(self):
        self.assertIsNone(self.module._safe_parse_dt("invalid-date"))


if __name__ == "__main__":
    unittest.main()
