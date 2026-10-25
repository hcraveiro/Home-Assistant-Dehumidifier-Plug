"""Verify config-entry setup, recovery and reload lifecycle."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"
package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
package.__path__ = [str(BASE)]

def module(name):
    return sys.modules.setdefault(name, types.ModuleType(name))

class EntryError(Exception):
    pass

def load():
    entries = module("homeassistant.config_entries")
    entries.ConfigEntry = object
    entries.ConfigEntryError = EntryError
    core = module("homeassistant.core")
    core.HomeAssistant = object
    module("homeassistant.helpers.typing").ConfigType = dict
    module("homeassistant.const").Platform = SimpleNamespace(SENSOR="sensor", SWITCH="switch")
    from dehumidifier_plug import models
    fake = module("dehumidifier_plug.coordinator")
    fake.DehumidifierCoordinator = Mock()
    key = "dehumidifier_plug.__init__"
    spec = importlib.util.spec_from_file_location(key, BASE / "__init__.py")
    integration = importlib.util.module_from_spec(spec)
    sys.modules[key] = integration
    spec.loader.exec_module(integration)
    return integration, fake

integration, fake_coordinator = load()
data = {
    "name": "WC", "switch_entity": "switch.plug",
    "power_sensor": "sensor.power", "humidity_sensor": "sensor.humidity",
    "start_time": "09:00:00", "end_time": "20:00:00",
}
class Entry:
    def __init__(self, values=None, options=None):
        self.data = data.copy() if values is None else values
        self.options = options or {}
        self.title = "WC"
        self.entry_id = "entry-1"
        self.listeners = []
    def add_update_listener(self, cb):
        self.listeners.append(cb)
        return lambda: None
    def async_on_unload(self, cb):
        self.cleanup = cb

class SetupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(
                async_forward_entry_setups=AsyncMock(),
                async_unload_platforms=AsyncMock(return_value=True),
                async_reload=AsyncMock(),
            ),
        )
        self.coord = SimpleNamespace(async_config_entry_first_refresh=AsyncMock())
        fake_coordinator.DehumidifierCoordinator.return_value = self.coord

    async def test_setup_starts_and_forwards(self):
        entry = Entry()
        self.assertTrue(await integration.async_setup_entry(self.hass, entry))
        self.assertEqual(len(entry.listeners), 1)
        self.assertIs(self.hass.data["dehumidifier_plug"][entry.entry_id]["coordinator"], self.coord)
        self.hass.config_entries.async_forward_entry_setups.assert_awaited_once()

    async def test_missing_power_can_be_recovered_via_options(self):
        entry = Entry({k: v for k, v in data.items() if k != "power_sensor"})
        with self.assertRaises(EntryError):
            await integration.async_setup_entry(self.hass, entry)
        self.assertEqual(len(entry.listeners), 1)
        entry.options = {"power_sensor": "sensor.fixed"}
        self.assertTrue(await integration.async_setup_entry(self.hass, entry))
        self.assertEqual(fake_coordinator.DehumidifierCoordinator.call_args.args[1].power_sensor, "sensor.fixed")

    async def test_null_option_does_not_erase_sensor(self):
        entry = Entry(options={"power_sensor": None})
        self.assertTrue(await integration.async_setup_entry(self.hass, entry))
        self.assertEqual(fake_coordinator.DehumidifierCoordinator.call_args.args[1].power_sensor, "sensor.power")

    async def test_missing_humidity_rejected(self):
        entry = Entry({k: v for k, v in data.items() if k != "humidity_sensor"})
        with self.assertRaises(EntryError):
            await integration.async_setup_entry(self.hass, entry)

    async def test_unload_removes_coordinator(self):
        entry = Entry()
        await integration.async_setup_entry(self.hass, entry)
        self.assertTrue(await integration.async_unload_entry(self.hass, entry))
        self.assertNotIn(entry.entry_id, self.hass.data["dehumidifier_plug"])

    async def test_failed_unload_keeps_coordinator(self):
        entry = Entry()
        await integration.async_setup_entry(self.hass, entry)
        self.hass.config_entries.async_unload_platforms.return_value = False
        self.assertFalse(await integration.async_unload_entry(self.hass, entry))
        self.assertIn(entry.entry_id, self.hass.data["dehumidifier_plug"])

    async def test_options_listener_reloads_entry(self):
        entry = Entry()
        await integration.update_listener(self.hass, entry)
        self.hass.config_entries.async_reload.assert_awaited_once_with("entry-1")

if __name__ == "__main__":
    unittest.main()
