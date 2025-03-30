from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from .const import DOMAIN
from .utils import slugify

AUTO_CONTROL_SWITCH_KEY = "auto_control"

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entity_registry = async_get_entity_registry(hass)
    device_registry = async_get_device_registry(hass)
    entity_entry = entity_registry.async_get(coordinator.config.switch_entity)
    device_entry = device_registry.async_get(entity_entry.device_id) if entity_entry else None
    device_identifiers = device_entry.identifiers if device_entry else None

    async_add_entities([
        DehumidifierAutoControlSwitch(coordinator, device_identifiers)
    ])

class DehumidifierAutoControlSwitch(SwitchEntity):
    def __init__(self, coordinator, device_identifiers):
        self.coordinator = coordinator
        object_id = slugify(coordinator.config.name)
        self._attr_name = f"{coordinator.config.name} Control"
        self._attr_unique_id = f"dehumidifier_auto_control_{object_id}"
        self._attr_is_on = True
        self._device_identifiers = device_identifiers

    @property
    def is_on(self):
        return self._attr_is_on

    def turn_on(self, **kwargs):
        self._attr_is_on = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        self._attr_is_on = False
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        if self._device_identifiers:
            return {"identifiers": self._device_identifiers}
        return None