"""Behavioral entity tests using small Home Assistant interface stubs."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "dehumidifier_plug"


def load(name):
    package = sys.modules.setdefault("dehumidifier_plug", types.ModuleType("dehumidifier_plug"))
    package.__path__ = [str(ROOT)]
    module_name = "dehumidifier_plug." + name
    spec = importlib.util.spec_from_file_location(module_name, ROOT / (name + ".py"))
    obj = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = obj
    spec.loader.exec_module(obj)
    return obj


class EntityTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        fake_switch = types.ModuleType("homeassistant.components.switch")
        fake_switch.SwitchEntity = type("SwitchEntity", (), {
            "schedule_update_ha_state": lambda self: None,
        })
        fake_sensor = types.ModuleType("homeassistant.components.sensor")
        fake_sensor.SensorEntity = object
        fake_sensor.SensorEntityDescription = lambda **kw: SimpleNamespace(**kw)
        restore = types.ModuleType("homeassistant.helpers.restore_state")
        restore.RestoreEntity = type("RestoreEntity", (), {
            "async_added_to_hass": AsyncMock(),
            "async_get_last_state": AsyncMock(return_value=None),
        })
        registry = types.ModuleType("homeassistant.helpers.entity_registry")
        registry.async_get = Mock()
        device_registry = types.ModuleType("homeassistant.helpers.device_registry")
        device_registry.async_get = Mock()
        entity_helper = types.ModuleType("homeassistant.helpers.entity")
        entity_helper.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
        const = sys.modules.setdefault("homeassistant.const", types.ModuleType("homeassistant.const"))
        const.PERCENTAGE = "%"
        for name, value in {
            "homeassistant.components": types.ModuleType("homeassistant.components"),
            "homeassistant.components.switch": fake_switch,
            "homeassistant.components.sensor": fake_sensor,
            "homeassistant.helpers.restore_state": restore,
            "homeassistant.helpers.entity_registry": registry,
            "homeassistant.helpers.device_registry": device_registry,
            "homeassistant.helpers.entity": entity_helper,
        }.items():
            sys.modules[name] = value
        utils = types.ModuleType("dehumidifier_plug.utils")
        utils.slugify = lambda value: value.lower().replace(" ", "_")
        sys.modules[utils.__name__] = utils
        load("const")
        cls.switch = load("switch")
        cls.sensor = load("sensor")

    def setUp(self):
        self.coordinator = SimpleNamespace(
            config=SimpleNamespace(name="Suite", switch_entity="switch.plug"),
            data={}, last_update_success=True,
            async_request_refresh=AsyncMock(), async_add_listener=Mock(return_value=Mock()),
        )

    def test_sensor_state_priorities(self):
        entity = self.sensor.DehumidifierSensor(
            self.coordinator, "status", self.sensor.SENSOR_TYPES["status"], None
        )
        scenarios = [
            ({}, None),
            ({"is_full": True, "is_on": True}, "Full"),
            ({"is_on": True}, "Dehumidifying"),
            ({"manual_override": True}, "Dehumidifying"),
            ({"inside_schedule": False}, "Outside dehumidifying hours"),
            ({"inside_schedule": True, "humidity_low": True}, "Below target humidity"),
            ({"inside_schedule": True, "humidity_low": False}, "Idle"),
        ]
        for data, expected in scenarios:
            with self.subTest(data=data):
                self.coordinator.data = data
                self.assertEqual(entity.native_value, expected)

    def test_status_availability_and_device(self):
        entity = self.sensor.DehumidifierSensor(
            self.coordinator, "status", self.sensor.SENSOR_TYPES["status"],
            {("plug", "1")},
        )
        self.assertEqual(entity.device_info, {"identifiers": {("plug", "1")}})
        self.assertTrue(entity.available)
        self.coordinator.last_update_success = False
        self.assertFalse(entity.available)

    async def test_sensor_refresh(self):
        entity = self.sensor.DehumidifierSensor(
            self.coordinator, "status", self.sensor.SENSOR_TYPES["status"], None
        )
        await entity.async_update()
        self.coordinator.async_request_refresh.assert_awaited_once()

    def test_auto_switch_toggles(self):
        entity = self.switch.DehumidifierAutoControlSwitch(self.coordinator, None)
        self.assertTrue(entity.is_on)
        self.assertEqual(entity._attr_unique_id, "dehumidifier_suite_control")
        entity.turn_off()
        self.assertFalse(entity.is_on)
        entity.turn_on()
        self.assertTrue(entity.is_on)

    async def test_auto_switch_restores_off(self):
        entity = self.switch.DehumidifierAutoControlSwitch(self.coordinator, None)
        entity.async_get_last_state = AsyncMock(return_value=SimpleNamespace(state="off"))
        await entity.async_added_to_hass()
        self.assertFalse(entity.is_on)

    async def test_auto_switch_keeps_default_without_previous_state(self):
        entity = self.switch.DehumidifierAutoControlSwitch(self.coordinator, None)
        entity.async_get_last_state = AsyncMock(return_value=None)
        await entity.async_added_to_hass()
        self.assertTrue(entity.is_on)


if __name__ == "__main__":
    unittest.main()
