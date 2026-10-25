"""Behavioral checks for entity state mapping, control and date helpers."""
import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"
pkg = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
pkg.__path__ = [str(BASE)]

def fake_module(name, **values):
    module = sys.modules.setdefault(name, types.ModuleType(name))
    for key, value in values.items():
        setattr(module, key, value)
    return module

fake_module("homeassistant")
fake_module("homeassistant.components")
fake_module("homeassistant.helpers")
fake_module("homeassistant.util")
fake_module("homeassistant.const", PERCENTAGE="%")
fake_module("homeassistant.helpers.entity", EntityCategory=SimpleNamespace(DIAGNOSTIC="diagnostic"))
fake_module("homeassistant.helpers.entity_registry", async_get=lambda hass: hass.entity_registry)
fake_module("homeassistant.helpers.device_registry", async_get=lambda hass: hass.device_registry)
fake_module("homeassistant.components.sensor",
            SensorEntity=type("SensorEntity", (), {
                "async_on_remove": lambda self, fn: None,
                "async_write_ha_state": lambda self: None,
            }),
            SensorEntityDescription=lambda **kwargs: SimpleNamespace(**kwargs))
fake_module("homeassistant.components.switch",
            SwitchEntity=type("SwitchEntity", (), {
                "async_added_to_hass": AsyncMock(),
                "schedule_update_ha_state": lambda self: None,
            }))
fake_module("homeassistant.helpers.restore_state",
            RestoreEntity=type("RestoreEntity", (), {
                "async_get_last_state": AsyncMock(return_value=None),
            }))
fake_module("homeassistant.util.dt", parse_datetime=lambda value: datetime.fromisoformat(value))
sys.modules["homeassistant.util"].dt = sys.modules["homeassistant.util.dt"]

def load(name):
    key = f"dehumidifier_plug.{name}"
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, BASE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module

load("const")
utils = load("utils")
sensor = load("sensor")
switch = load("switch")


class UtilsTests(unittest.TestCase):
    def test_slug_removes_accents_and_punctuation(self):
        self.assertEqual(utils.slugify("WC Suíte - Déshumidifier!"), "wc_suite_deshumidifier")

    def test_naive_datetime_becomes_utc(self):
        result = utils._safe_parse_dt("2026-10-25T20:00:00")
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_aware_datetime_preserves_offset(self):
        item = datetime.fromisoformat("2026-10-25T20:00:00+01:00")
        self.assertEqual(utils._safe_parse_dt(item), item)

    def test_naive_datetime_object(self):
        result = utils._safe_parse_dt(datetime(2026, 10, 25))
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_invalid_storage_values(self):
        for value in (None, "", " ", 45, "not a date"):
            with self.subTest(value=value):
                self.assertIsNone(utils._safe_parse_dt(value))


class StatusSensorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = SimpleNamespace(
            config=SimpleNamespace(name="Test"),
            data={}, last_update_success=True,
            async_request_refresh=AsyncMock(),
            async_add_listener=Mock(return_value=lambda: None),
        )
        self.entity = sensor.DehumidifierSensor(
            self.coordinator, "status", sensor.SENSOR_TYPES["status"], {("plug", "1")}
        )

    def test_priority_and_states(self):
        cases = [
            (None, None),
            ({"is_full": True, "is_on": True}, "Full"),
            ({"is_on": True}, "Dehumidifying"),
            ({"manual_override": True}, "Dehumidifying"),
            ({"inside_schedule": False}, "Outside dehumidifying hours"),
            ({"inside_schedule": True, "humidity_low": True}, "Below target humidity"),
            ({"inside_schedule": True, "humidity_low": False}, "Idle"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.coordinator.data = value
                self.assertEqual(self.entity.native_value, expected)

    def test_availability(self):
        self.assertTrue(self.entity.available)
        self.coordinator.last_update_success = False
        self.assertFalse(self.entity.available)

    def test_device_info(self):
        self.assertEqual(self.entity.device_info["identifiers"], {("plug", "1")})
        self.entity._device_identifiers = None
        self.assertIsNone(self.entity.device_info)

    async def test_refresh(self):
        await self.entity.async_update()
        self.coordinator.async_request_refresh.assert_awaited_once()


class ControlSwitchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = SimpleNamespace(config=SimpleNamespace(name="Test"))
        self.entity = switch.DehumidifierAutoControlSwitch(
            self.coordinator, {("plug", "1")}
        )
        self.entity.schedule_update_ha_state = Mock()

    def test_control_switch_defaults_to_on(self):
        self.assertTrue(self.entity.is_on)
        self.assertEqual(self.entity.device_info["identifiers"], {("plug", "1")})

    def test_turn_off_and_on(self):
        self.entity.turn_off()
        self.assertFalse(self.entity.is_on)
        self.entity.turn_on()
        self.assertTrue(self.entity.is_on)
        self.assertEqual(self.entity.schedule_update_ha_state.call_count, 2)

    async def test_restore_off(self):
        self.entity.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="off"))
        await self.entity.async_added_to_hass()
        self.assertFalse(self.entity.is_on)

    async def test_restore_on(self):
        self.entity._attr_is_on = False
        self.entity.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="on"))
        await self.entity.async_added_to_hass()
        self.assertTrue(self.entity.is_on)

    async def test_no_previous_state_keeps_default(self):
        self.entity.async_get_last_state = AsyncMock(return_value=None)
        await self.entity.async_added_to_hass()
        self.assertTrue(self.entity.is_on)

    def test_no_device(self):
        self.entity._device_identifiers = None
        self.assertIsNone(self.entity.device_info)


if __name__ == "__main__":
    unittest.main()
