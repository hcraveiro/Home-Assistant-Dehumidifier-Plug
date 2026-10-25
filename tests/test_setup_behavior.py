"""Behavioral tests for setup, options recovery, and entry reloads."""
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"


def load_module(name):
    module_name = "dehumidifier_plug." + name
    spec = importlib.util.spec_from_file_location(module_name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SetupTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
        package.__path__ = [str(ROOT)]
        config_entries = sys.modules.setdefault("homeassistant.config_entries", types.ModuleType("homeassistant.config_entries"))
        config_entries.ConfigEntry = object
        config_entries.ConfigEntryError = type("ConfigEntryError", (Exception,), {})
        core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
        core.HomeAssistant = object
        typing_module = sys.modules.setdefault("homeassistant.helpers.typing", types.ModuleType("homeassistant.helpers.typing"))
        typing_module.ConfigType = dict
        const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
        const.Platform = SimpleNamespace(SENSOR="sensor", SWITCH="switch")
        load_module("const")
        load_module("models")
        fake_coordinator = types.ModuleType("dehumidifier_plug.coordinator")
        fake_coordinator.DehumidifierCoordinator = Mock()
        sys.modules["dehumidifier_plug.coordinator"] = fake_coordinator
        cls.module = load_module("__init__")
        cls.error_type = config_entries.ConfigEntryError

    def entry(self, **overrides):
        data = {
            "switch_entity": "switch.plug", "power_sensor": "sensor.power",
            "humidity_sensor": "sensor.humidity", "full_power_threshold": 2,
            "humidity_on_threshold": 60, "humidity_off_threshold": 50,
            "start_time": "09:00:00", "end_time": "20:00:00",
        }
        data.update(overrides)
        entry = SimpleNamespace(
            data=data, options={}, title="Bathroom", entry_id="entry-1",
            add_update_listener=Mock(return_value=Mock()),
            async_on_unload=Mock(),
        )
        hass = SimpleNamespace(
            data={}, config_entries=SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
            ),
        )
        return hass, entry

    async def test_setup_loads_and_merges_options(self):
        hass, entry = self.entry()
        entry.options = {"power_sensor": "sensor.new", "weekdays": ["mon"],
                         "time_windows": [{"start": "11:00", "end": "12:00"}]}
        with patch.object(self.module, "DehumidifierCoordinator") as factory:
            factory.return_value.async_config_entry_first_refresh = AsyncMock()
            self.assertTrue(await self.module.async_setup_entry(hass, entry))
            self.assertEqual(factory.call_args.args[1].power_sensor, "sensor.new")
            self.assertEqual(factory.call_args.args[1].weekdays, ["mon"])
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()
        entry.add_update_listener.assert_called_once()

    async def test_missing_power_registers_listener_before_error(self):
        hass, entry = self.entry(power_sensor=None)
        with self.assertRaises(self.error_type):
            await self.module.async_setup_entry(hass, entry)
        entry.async_on_unload.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_not_awaited()

    async def test_none_option_does_not_override_valid_sensor(self):
        hass, entry = self.entry()
        entry.options = {"power_sensor": None}
        with patch.object(self.module, "DehumidifierCoordinator") as factory:
            factory.return_value.async_config_entry_first_refresh = AsyncMock()
            await self.module.async_setup_entry(hass, entry)
            self.assertEqual(factory.call_args.args[1].power_sensor, "sensor.power")

    async def test_update_listener_reloads_entry(self):
        hass, entry = self.entry()
        await self.module.update_listener(hass, entry)
        hass.config_entries.async_reload.assert_awaited_once_with("entry-1")

    async def test_unload_removes_coordinator(self):
        hass, entry = self.entry()
        hass.data["dehumidifier_plug"] = {"entry-1": {"coordinator": object()}}
        self.assertTrue(await self.module.async_unload_entry(hass, entry))
        self.assertNotIn("entry-1", hass.data["dehumidifier_plug"])

    async def test_failed_unload_preserves_coordinator(self):
        hass, entry = self.entry()
        hass.data["dehumidifier_plug"] = {"entry-1": {"coordinator": object()}}
        hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await self.module.async_unload_entry(hass, entry))
        self.assertIn("entry-1", hass.data["dehumidifier_plug"])


if __name__ == "__main__":
    unittest.main()
