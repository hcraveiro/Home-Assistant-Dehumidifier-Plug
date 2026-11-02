"""Exercise coordinator control decisions without a Home Assistant installation."""
import asyncio
import importlib.util
import logging
import sys
import types
import unittest
from datetime import datetime, time, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"
package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
package.__path__ = [str(BASE)]

def load(name):
    key = f"dehumidifier_plug.{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, BASE / f"{name}.py")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[key] = obj
    spec.loader.exec_module(obj)
    return obj

core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
coordinator.DataUpdateCoordinator = type("DataUpdateCoordinator", (), {})
coordinator.UpdateFailed = type("UpdateFailed", (Exception,), {})
interval = types.ModuleType("homeassistant.helpers.entity_component")
interval.DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
storage = types.ModuleType("homeassistant.helpers.storage")
storage.Store = object
dt = types.ModuleType("homeassistant.util.dt")
dt.now = lambda: datetime(2026, 10, 26, 10, tzinfo=timezone.utc)
dt.utcnow = dt.now
for name, mod in {
    "homeassistant": types.ModuleType("homeassistant"),
    "homeassistant.core": core,
    "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
    "homeassistant.helpers.update_coordinator": coordinator,
    "homeassistant.helpers.entity_component": interval,
    "homeassistant.helpers.storage": storage,
    "homeassistant.util": types.ModuleType("homeassistant.util"),
    "homeassistant.util.dt": dt,
}.items():
    sys.modules.setdefault(name, mod)
sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.util"].dt = dt
load("const")
load("models")
load("schedule")
utils = types.ModuleType("dehumidifier_plug.utils")
utils.slugify = lambda value: value.lower().replace(" ", "_")
utils._safe_parse_dt = lambda value: None
sys.modules["dehumidifier_plug.utils"] = utils
Coordinator = load("coordinator").DehumidifierCoordinator
Config = load("models").DehumidifierConfig
CONFIG = {
    "name": "Test", "switch_entity": "switch.plug", "power_sensor": "sensor.power",
    "humidity_sensor": "sensor.humidity", "full_power_threshold": 2,
    "humidity_on_threshold": 60, "humidity_off_threshold": 50,
    "time_windows": [{"start": "09:00", "end": "20:00"}],
    "weekdays": ["mon"],
}

class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    def create(self, switch="off", power="0", humidity="70", auto="on", inside=True):
        self.unit = object.__new__(Coordinator)
        self.unit.config = Config.from_dict(CONFIG)
        self.unit._last_auto_on = None
        self.unit._power_low_since = None
        self.unit._manual_override = False
        self.unit._last_switch_state = switch
        self.unit._auto_turning_on = False
        self.unit._is_full_latched = False
        self.unit._auto_control_enabled = True
        self.unit.auto_control = SimpleNamespace(is_on=auto == "on", ready=True)
        self.unit.save_persistent_data = AsyncMock()
        states = {
            "switch.plug": SimpleNamespace(state=switch),
            "sensor.power": SimpleNamespace(state=power, attributes={}),
            "sensor.humidity": SimpleNamespace(state=humidity, attributes={}),
            "switch.test_control": SimpleNamespace(state=auto),
        }
        self.unit.hass = SimpleNamespace(
            states=SimpleNamespace(get=states.get),
            services=SimpleNamespace(async_call=AsyncMock()),
        )
        dt.now = (lambda: datetime(2026, 10, 26, 10 if inside else 22, tzinfo=timezone.utc))
        dt.utcnow = dt.now
        return states

    async def test_high_humidity_starts(self):
        self.create()
        data = await self.unit._async_update_data()
        self.assertTrue(data["inside_schedule"])
        self.unit.hass.services.async_call.assert_awaited_once()
        self.assertEqual(self.unit.hass.services.async_call.call_args.args[:2], ("switch", "turn_on"))

    async def test_low_humidity_stops(self):
        self.create(switch="on", power="150", humidity="40")
        await self.unit._async_update_data()
        self.assertEqual(self.unit.hass.services.async_call.call_args.args[:2], ("switch", "turn_off"))

    async def test_hysteresis_does_not_start(self):
        self.create(humidity="55")
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_disabled_auto_does_not_start(self):
        self.create(auto="off")
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_outside_schedule_does_not_start(self):
        self.create(inside=False)
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_outside_schedule_stops_running(self):
        self.create(switch="on", power="150", inside=False)
        await self.unit._async_update_data()
        self.assertEqual(self.unit.hass.services.async_call.call_args.args[:2], ("switch", "turn_off"))

    async def test_manual_override_kept_outside_schedule(self):
        self.create(switch="on", power="150", inside=False)
        self.unit._manual_override = True
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_manual_override_cleared_on_switch_off(self):
        states = self.create(switch="off")
        self.unit._last_switch_state = "on"
        self.unit._manual_override = True
        await self.unit._async_update_data()
        self.assertFalse(self.unit._manual_override)

    async def test_manual_turn_on_detected(self):
        self.create(switch="on", power="150", humidity="55", auto="off")
        self.unit._last_switch_state = "off"
        result = await self.unit._async_update_data()
        self.assertTrue(result["manual_override"])

    async def test_full_tank_after_60_seconds(self):
        self.create(switch="on", power="0", humidity="70")
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=61)
        result = await self.unit._async_update_data()
        self.assertTrue(result["is_full"])
        self.assertTrue(self.unit._is_full_latched)

    async def test_power_recovery_clears_full_latch(self):
        self.create(switch="on", power="150", humidity="55")
        self.unit._is_full_latched = True
        result = await self.unit._async_update_data()
        self.assertFalse(result["is_full"])

    async def test_unavailable_sensor_fails_safe(self):
        self.create(power="unavailable")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()


    async def test_exact_upper_limit_does_not_start(self):
        self.create(humidity="60")
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_exact_lower_limit_does_not_stop(self):
        self.create(switch="on", power="150", humidity="50")
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_below_lower_limit_stops_outside_window_even_manual(self):
        self.create(switch="on", power="150", humidity="45", inside=False)
        self.unit._manual_override = True
        await self.unit._async_update_data()
        self.assertEqual(self.unit.hass.services.async_call.call_args.args[:2], ("switch", "turn_off"))

    async def test_low_power_before_full_timeout(self):
        self.create(switch="on", power="0")
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=59)
        result = await self.unit._async_update_data()
        self.assertFalse(result["is_full"])

    async def test_low_power_exactly_at_full_timeout(self):
        self.create(switch="on", power="0")
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=60)
        result = await self.unit._async_update_data()
        self.assertTrue(result["is_full"])

    async def test_full_latch_still_blocks_no_commands_when_running(self):
        self.create(switch="on", power="0")
        self.unit._is_full_latched = True
        result = await self.unit._async_update_data()
        self.assertTrue(result["is_full"])
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_unknown_humidity_fails_without_switching(self):
        self.create(humidity="unknown")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_non_numeric_power_fails_without_switching(self):
        self.create(power="not-a-number")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_service_call_failure_is_reported(self):
        self.create()
        self.unit.hass.services.async_call.side_effect = RuntimeError("service unavailable")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()

    async def test_missing_sensor_fails_safe(self):
        states = self.create()
        del states["sensor.power"]
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()

    async def test_unavailable_plug_does_not_send_command_and_recovers(self):
        states = self.create(switch="unavailable")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.assertIn("switch.plug", self.unit.unavailable_reason)
        self.unit.hass.services.async_call.assert_not_awaited()
        states["switch.plug"].state = "off"
        await self.unit._async_update_data()
        self.assertIsNone(self.unit.unavailable_reason)
        self.unit.hass.services.async_call.assert_awaited_once()

    async def test_control_reference_does_not_depend_on_entity_id(self):
        states = self.create()
        del states["switch.test_control"]
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_awaited_once()

    async def test_control_not_used_until_restored(self):
        self.create()
        self.unit.auto_control.ready = False
        await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_timeout_is_configurable(self):
        self.create(switch="on", power="0")
        self.unit.config.full_timeout = 120
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=61)
        self.assertFalse((await self.unit._async_update_data())["is_full"])
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=120)
        self.assertTrue((await self.unit._async_update_data())["is_full"])

    async def test_sensor_gap_resets_pending_full_timer(self):
        states = self.create(switch="on", power="unavailable")
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=30)
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.assertIsNone(self.unit._power_low_since)
        states["sensor.power"].state = "0"
        self.assertFalse((await self.unit._async_update_data())["is_full"])

    async def test_nonfinite_value_is_rejected(self):
        self.create(humidity="nan")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_invalid_switch_state_is_not_treated_as_off(self):
        self.create(switch="unexpected")
        with self.assertRaises(coordinator.UpdateFailed):
            await self.unit._async_update_data()
        self.unit.hass.services.async_call.assert_not_awaited()

    async def test_power_in_kw_is_converted(self):
        states = self.create(switch="on", power="0.15", humidity="55")
        states["sensor.power"].attributes["unit_of_measurement"] = "kW"
        data = await self.unit._async_update_data()
        self.assertFalse(data["is_full"])
        self.assertIsNone(self.unit._power_low_since)

    async def test_full_notification_only_once_per_latch(self):
        self.create(switch="on", power="0")
        self.unit.config.notifications_enabled = True
        self.unit._notify_full = AsyncMock()
        self.unit.hass.async_create_task = lambda coro: asyncio.create_task(coro)
        self.unit._power_low_since = dt.utcnow() - timedelta(seconds=60)
        await self.unit._async_update_data()
        await asyncio.sleep(0)
        await self.unit._async_update_data()
        self.unit._notify_full.assert_awaited_once()

    async def test_notification_delivers_to_unique_mobile_targets(self):
        self.create()
        translation = types.ModuleType("homeassistant.helpers.translation")
        translation.async_get_translations = AsyncMock(return_value={
            "component.dehumidifier_plug.common.possible_full": "{name} may be full"})
        sys.modules[translation.__name__] = translation
        self.unit.hass.config = SimpleNamespace(language="en")
        self.unit.config.notification_targets = ["notify.mobile_app_phone", "notify.mobile_app_phone", "notify.bad"]
        await self.unit._notify_full()
        self.unit.hass.services.async_call.assert_awaited_once_with(
            "notify", "mobile_app_phone", {"message": "Test may be full"}, blocking=True)

    async def test_notification_falls_back_and_continues_after_failure(self):
        self.create()
        translation = types.ModuleType("homeassistant.helpers.translation")
        translation.async_get_translations = AsyncMock(return_value={})
        sys.modules[translation.__name__] = translation
        self.unit.hass.config = SimpleNamespace(language="en")
        self.unit.config.notification_targets = ["notify.mobile_app_a", "notify.mobile_app_b"]
        self.unit.hass.services.async_call.side_effect = [RuntimeError("offline"), None]
        await self.unit._notify_full()
        self.assertEqual(self.unit.hass.services.async_call.await_count, 2)

    async def test_load_restores_latch_but_does_not_count_downtime(self):
        self.create()
        self.unit.storage = SimpleNamespace(async_load=AsyncMock(return_value={
            "power_low_since": "2026-01-01T00:00:00+00:00",
            "manual_override": True, "last_switch_state": "on", "is_full_latched": True,
        }))
        await self.unit.load_persistent_data()
        self.assertIsNone(self.unit._power_low_since)
        self.assertTrue(self.unit._is_full_latched)
        self.assertTrue(self.unit._manual_override)

if __name__ == "__main__":
    unittest.main()
