from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
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

class DehumidifierAutoControlSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, coordinator, device_identifiers):
        self.coordinator = coordinator
        coordinator.auto_control = self
        self.ready = False
        object_id = slugify(f"{coordinator.config.name}_control")
        self._attr_name = f"{coordinator.config.name} Control"
        self._attr_unique_id = f"dehumidifier_{object_id}"
        self._attr_is_on = True  # Default to on unless restored from previous state
        self._device_identifiers = device_identifiers

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        # Restore previous state after Home Assistant restarts
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.state in ("on", "off"):
                self._attr_is_on = old_state.state == "on"
            else:
                saved = self.coordinator._auto_control_enabled
                if saved is not None:
                    self._attr_is_on = saved
        elif self.coordinator._auto_control_enabled is not None:
            self._attr_is_on = self.coordinator._auto_control_enabled
        self.coordinator._auto_control_enabled = self._attr_is_on
        await self.coordinator.save_persistent_data()
        self.ready = True
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        return {
            "auto_control_enabled": self._attr_is_on,
            "unavailable_reason": getattr(self.coordinator, "unavailable_reason", None),
        }

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.coordinator._auto_control_enabled = True
        await self.coordinator.save_persistent_data()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.coordinator._auto_control_enabled = False
        await self.coordinator.save_persistent_data()
        self.async_write_ha_state()

    @property
    def device_info(self):
        if self._device_identifiers:
            return {"identifiers": self._device_identifiers}
        return None
