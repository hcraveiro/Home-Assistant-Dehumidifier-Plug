"""Schedule and migration tests without requiring Home Assistant runtime."""
import sys
import types
import unittest
from datetime import datetime, time
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"
package = types.ModuleType("dehumidifier_plug")
package.__path__ = [str(BASE)]
sys.modules["dehumidifier_plug"] = package


def load(name):
    spec = spec_from_file_location(f"dehumidifier_plug.{name}", BASE / f"{name}.py")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


schedule = load("schedule")
models = load("models")
BASE_CONFIG = {
    "name": "Test", "switch_entity": "switch.plug",
    "power_sensor": "sensor.power", "humidity_sensor": "sensor.humidity",
    "full_power_threshold": 2, "humidity_on_threshold": 60,
    "humidity_off_threshold": 50, "start_time": "09:00:00",
    "end_time": "20:00:00",
}


class ScheduleTests(unittest.TestCase):
    def active(self, day, hour, minute, weekdays, windows):
        return schedule.is_in_schedule(
            datetime(2026, 10, day, hour, minute),
            weekdays, [(time.fromisoformat(a), time.fromisoformat(b)) for a, b in windows],
        )

    def test_weekday_allowed(self):
        self.assertTrue(self.active(26, 9, 0, ["mon"], [("09:00", "10:00")]))

    def test_weekday_disallowed(self):
        self.assertFalse(self.active(27, 9, 0, ["mon"], [("09:00", "10:00")]))

    def test_exact_end_excluded(self):
        self.assertFalse(self.active(26, 10, 0, ["mon"], [("09:00", "10:00")]))

    def test_early_start_excluded(self):
        self.assertFalse(self.active(26, 8, 59, ["mon"], [("09:00", "10:00")]))

    def test_second_window(self):
        self.assertTrue(self.active(26, 18, 30, ["mon"], [("09:00", "10:00"), ("18:00", "19:00")]))

    def test_gap_between_windows(self):
        self.assertFalse(self.active(26, 12, 0, ["mon"], [("09:00", "10:00"), ("18:00", "19:00")]))

    def test_overnight_on_start_day(self):
        self.assertTrue(self.active(26, 23, 0, ["mon"], [("22:00", "02:00")]))

    def test_overnight_on_next_day(self):
        self.assertTrue(self.active(27, 1, 0, ["mon"], [("22:00", "02:00")]))

    def test_overnight_next_day_end_excluded(self):
        self.assertFalse(self.active(27, 2, 0, ["mon"], [("22:00", "02:00")]))

    def test_empty_days(self):
        self.assertFalse(self.active(26, 9, 0, [], [("09:00", "10:00")]))

    def test_empty_windows(self):
        self.assertFalse(self.active(26, 9, 0, ["mon"], []))

    def test_equal_time_full_day(self):
        self.assertTrue(self.active(26, 21, 0, ["mon"], [("09:00", "09:00")]))

    def test_overlapping_intervals(self):
        self.assertTrue(self.active(26, 11, 0, ["mon"], [("09:00", "12:00"), ("10:00", "13:00")]))

    def test_no_overnight_when_start_day_unselected(self):
        self.assertFalse(self.active(27, 1, 0, ["tue"], [("22:00", "02:00")]))


class MigrationTests(unittest.TestCase):
    def test_existing_schedule_retained(self):
        cfg = models.DehumidifierConfig.from_dict(BASE_CONFIG)
        self.assertEqual(cfg.time_windows, [(time(9), time(20))])
        self.assertEqual(cfg.weekdays, list(schedule.WEEKDAYS))

    def test_legacy_option_schedule_wins(self):
        data = models.merge_entry_settings(BASE_CONFIG, {"start_time": "11:00:00", "end_time": "12:00:00"})
        self.assertEqual(models.DehumidifierConfig.from_dict(data).time_windows, [(time(11), time(12))])

    def test_new_windows_replace_legacy(self):
        data = models.merge_entry_settings(BASE_CONFIG, {
            "time_windows": [{"start": "06:00", "end": "07:00"}, {"start": "18:00", "end": "19:00"}],
            "weekdays": ["mon", "fri"],
        })
        cfg = models.DehumidifierConfig.from_dict(data)
        self.assertEqual(cfg.time_windows, [(time(6), time(7)), (time(18), time(19))])
        self.assertEqual(cfg.weekdays, ["mon", "fri"])

    def test_null_power_option_preserves_entity(self):
        self.assertEqual(models.merge_entry_settings(BASE_CONFIG, {"power_sensor": None})["power_sensor"], "sensor.power")

    def test_new_power_and_switch_options(self):
        merged = models.merge_entry_settings(BASE_CONFIG, {
            "switch_entity": "switch.new", "power_sensor": "sensor.new",
        })
        cfg = models.DehumidifierConfig.from_dict(merged)
        self.assertEqual((cfg.switch_entity, cfg.power_sensor), ("switch.new", "sensor.new"))

    def test_existing_thresholds_retained(self):
        cfg = models.DehumidifierConfig.from_dict(BASE_CONFIG)
        self.assertEqual((cfg.full_power_threshold, cfg.humidity_on_threshold, cfg.humidity_off_threshold), (2, 60, 50))

    def test_defaults_without_legacy_schedule(self):
        data = {k: v for k, v in BASE_CONFIG.items() if k not in ("start_time", "end_time")}
        self.assertEqual(models.DehumidifierConfig.from_dict(data).time_windows, [(time(9), time(20))])

    def test_time_objects_accepted(self):
        data = {**BASE_CONFIG, "time_windows": [{"start": time(8), "end": time(9)}]}
        self.assertEqual(models.DehumidifierConfig.from_dict(data).time_windows, [(time(8), time(9))])

    def test_missing_threshold_defaults(self):
        data = {k: v for k, v in BASE_CONFIG.items() if not k.endswith("threshold") and not k.startswith("humidity_o")}
        cfg = models.DehumidifierConfig.from_dict(data)
        self.assertEqual((cfg.full_power_threshold, cfg.humidity_on_threshold, cfg.humidity_off_threshold), (2, 60, 50))


if __name__ == "__main__":
    unittest.main()
