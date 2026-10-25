"""Exercise config and options forms with representative Home Assistant stubs."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"

def fake_selector(*args, **kwargs):
    return lambda value: value

class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
        package.__path__ = [str(ROOT)]
        config_entries = types.ModuleType("homeassistant.config_entries")
        class ConfigFlow:
            def __init_subclass__(cls, **kwargs):
                pass
            def async_create_entry(self, **kwargs):
                return {"type": "create_entry", **kwargs}
            def async_show_form(self, **kwargs):
                return {"type": "form", **kwargs}
        class OptionsFlow(ConfigFlow):
            pass
        config_entries.ConfigFlow = ConfigFlow
        config_entries.OptionsFlow = OptionsFlow
        config_entries.ConfigEntry = object
        sys.modules["homeassistant.config_entries"] = config_entries
        core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
        core.callback = lambda func: func
        selectors = types.ModuleType("homeassistant.helpers.selector")
        selectors.SelectOptionDict = lambda **kw: kw
        selectors.SelectSelector = fake_selector
        selectors.SelectSelectorConfig = lambda **kw: kw
        selectors.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
        selectors.ObjectSelector = fake_selector
        selectors.ObjectSelectorConfig = lambda **kw: kw
        selectors.TimeSelector = fake_selector
        selectors.EntitySelector = fake_selector
        selectors.EntitySelectorConfig = lambda **kw: kw
        selectors.TextSelector = fake_selector
        selectors.NumberSelector = fake_selector
        selectors.NumberSelectorConfig = lambda **kw: kw
        selectors.NumberSelectorMode = SimpleNamespace(BOX="box")
        sys.modules["homeassistant.helpers.selector"] = selectors
        helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
        helpers.selector = selectors
        spec = importlib.util.spec_from_file_location("dehumidifier_plug.config_flow", ROOT / "config_flow.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cls.flow = module

    async def test_options_initial_load_migrates_legacy_interval(self):
        entry = SimpleNamespace(data={
            "switch_entity": "switch.old", "power_sensor": "sensor.power",
            "humidity_sensor": "sensor.humidity", "start_time": "11:00:00",
            "end_time": "12:00:00",
        }, options={})
        handler = self.flow.DehumidifierOptionsFlowHandler()
        handler.config_entry = entry
        response = await handler.async_step_init()
        self.assertEqual(response["type"], "form")
        keys = {key.schema: key.default() for key in response["data_schema"].schema
                if callable(getattr(key, "default", None))}
        self.assertEqual(keys["time_windows"], [{"start": "11:00:00", "end": "12:00:00"}])
        self.assertEqual(keys["weekdays"], ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        self.assertEqual(keys["switch_entity"], "switch.old")

    async def test_options_submit_keeps_entities_and_windows(self):
        entry = SimpleNamespace(data={}, options={})
        handler = self.flow.DehumidifierOptionsFlowHandler()
        handler.config_entry = entry
        settings = {
            "switch_entity": "switch.new", "power_sensor": "sensor.new",
            "humidity_sensor": "sensor.rh", "weekdays": ["fri"],
            "time_windows": [{"start": "18:00", "end": "19:00"}],
        }
        result = await handler.async_step_init(settings)
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"], settings)

    async def test_invalid_options_show_translated_error(self):
        handler = self.flow.DehumidifierOptionsFlowHandler()
        handler.config_entry = SimpleNamespace(data={}, options={})
        result = await handler.async_step_init({"time_windows": []})
        self.assertEqual(result["errors"], {"base": "invalid_schedule"})

    async def test_new_entry_validation(self):
        flow = self.flow.DehumidifierConfigFlow()
        form = await flow.async_step_user({"time_windows": [{"start": "10:00"}]})
        self.assertEqual(form["errors"], {"base": "invalid_schedule"})
        success = await flow.async_step_user({
            "name": "Bedroom",
            "time_windows": [{"start": "10:00", "end": "11:00"}],
            "weekdays": ["sat"],
        })
        self.assertEqual(success["type"], "create_entry")
        self.assertEqual(success["title"], "Bedroom")

    async def test_missing_power_option_has_no_default(self):
        handler = self.flow.DehumidifierOptionsFlowHandler()
        handler.config_entry = SimpleNamespace(
            data={"switch_entity": "switch.plug", "humidity_sensor": "sensor.rh"},
            options={"power_sensor": None},
        )
        response = await handler.async_step_init()
        power = next(k for k in response["data_schema"].schema if k.schema == "power_sensor")
        self.assertFalse(callable(getattr(power, "default", None)))


if __name__ == "__main__":
    unittest.main()
