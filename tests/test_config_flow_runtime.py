"""Exercise setup/options submissions with Home Assistant selector substitutes."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"
package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
package.__path__ = [str(BASE)]

def module(name):
    return sys.modules.setdefault(name, types.ModuleType(name))

class FakeConfigFlow:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}
    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

class FakeOptionsFlow(FakeConfigFlow):
    pass

class FakeSelector:
    def __init__(self, config=None):
        self.config = config
    def __call__(self, value):
        return value

def selector_config(**kwargs):
    return SimpleNamespace(**kwargs)

def install():
    import voluptuous
    ha = module("homeassistant")
    core = module("homeassistant.core")
    core.callback = lambda value: value
    entry = module("homeassistant.config_entries")
    entry.ConfigFlow = FakeConfigFlow
    entry.OptionsFlow = FakeOptionsFlow
    entry.ConfigEntry = object
    ha.config_entries = entry
    helpers = module("homeassistant.helpers")
    select = module("homeassistant.helpers.selector")
    for key in ("SelectSelector", "ObjectSelector", "EntitySelector",
                "TextSelector", "NumberSelector", "TimeSelector"):
        setattr(select, key, FakeSelector)
    for key in ("SelectSelectorConfig", "ObjectSelectorConfig", "EntitySelectorConfig",
                "NumberSelectorConfig"):
        setattr(select, key, selector_config)
    select.SelectOptionDict = selector_config
    select.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
    select.NumberSelectorMode = SimpleNamespace(BOX="box")
    helpers.selector = select
    module("homeassistant").helpers = helpers
    key = "dehumidifier_plug.config_flow"
    spec = importlib.util.spec_from_file_location(key, BASE / "config_flow.py")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[key] = obj
    spec.loader.exec_module(obj)
    return obj

flow = install()
legacy = {
    "name": "WC", "switch_entity": "switch.plug",
    "power_sensor": "sensor.power", "humidity_sensor": "sensor.humidity",
    "humidity_on_threshold": 60, "humidity_off_threshold": 50,
    "full_power_threshold": 2, "start_time": "09:00:00", "end_time": "20:00:00",
}
windows = [{"start": "10:00:00", "end": "11:00:00"}]
valid = {**legacy, "weekdays": ["mon", "wed"], "time_windows": windows}


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_uses_selected_values(self):
        output = await flow.DehumidifierConfigFlow().async_step_user(valid)
        self.assertEqual(output["type"], "create_entry")
        self.assertEqual(output["data"]["weekdays"], ["mon", "wed"])
        self.assertEqual(output["data"]["time_windows"], windows)

    async def test_empty_windows_rejected(self):
        output = await flow.DehumidifierConfigFlow().async_step_user(
            {**valid, "time_windows": []}
        )
        self.assertEqual(output["errors"]["base"], "invalid_schedule")

    async def test_incomplete_window_rejected(self):
        output = await flow.DehumidifierConfigFlow().async_step_user(
            {**valid, "time_windows": [{"start": "10:00"}]}
        )
        self.assertEqual(output["errors"]["base"], "invalid_schedule")

    async def test_initial_form_has_dynamic_intervals(self):
        output = await flow.DehumidifierConfigFlow().async_step_user()
        self.assertEqual(output["type"], "form")
        self.assertEqual(len(output["data_schema"].schema), 9)

    async def test_options_factory_accepts_config_entry(self):
        entry = SimpleNamespace(data=legacy, options={})
        obj = flow.DehumidifierConfigFlow.async_get_options_flow(entry)
        self.assertIs(obj._config_entry, entry)
        result = await obj.async_step_init()
        self.assertEqual(result["type"], "form")

    async def test_options_migrates_legacy_interval(self):
        obj = flow.DehumidifierOptionsFlowHandler(SimpleNamespace(data=legacy, options={}))
        obj._config_entry = SimpleNamespace(data=legacy, options={})
        output = await obj.async_step_init()
        defaults = {key.schema: key.default() for key in output["data_schema"].schema if hasattr(key, "default") and callable(key.default)}
        self.assertEqual(defaults["time_windows"], [{"start": "09:00:00", "end": "20:00:00"}])
        self.assertEqual(len(defaults["weekdays"]), 7)

    async def test_options_preserve_original_entity_for_null_override(self):
        obj = flow.DehumidifierOptionsFlowHandler(SimpleNamespace(data=legacy, options={"power_sensor": None}))
        output = await obj.async_step_init()
        defaults = {key.schema: key.default() for key in output["data_schema"].schema if hasattr(key, "default") and callable(key.default)}
        self.assertEqual(defaults["power_sensor"], "sensor.power")

    async def test_options_save_multiple_windows(self):
        obj = flow.DehumidifierOptionsFlowHandler(SimpleNamespace(data=legacy, options={}))
        output = await obj.async_step_init({**valid, "time_windows": windows * 2})
        self.assertEqual(output["type"], "create_entry")
        self.assertEqual(len(output["data"]["time_windows"]), 2)

    async def test_options_reject_empty_windows(self):
        obj = flow.DehumidifierOptionsFlowHandler(SimpleNamespace(data=legacy, options={}))
        output = await obj.async_step_init({**valid, "time_windows": []})
        self.assertEqual(output["errors"]["base"], "invalid_schedule")


if __name__ == "__main__":
    unittest.main()
