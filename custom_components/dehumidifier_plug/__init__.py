from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_SWITCH, CONF_POWER, CONF_HUMIDITY,
    CONF_FULL_THRESHOLD, CONF_HUMIDITY_ON, CONF_HUMIDITY_OFF,
    CONF_START_TIME, CONF_END_TIME
)
from .coordinator import DehumidifierCoordinator
from .models import DehumidifierConfig

PLATFORMS = ["sensor", "switch"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = DehumidifierConfig(
        name=entry.title,
        switch_entity=entry.data[CONF_SWITCH],
        power_sensor=entry.data[CONF_POWER],
        humidity_sensor=entry.data[CONF_HUMIDITY],
        full_power_threshold=entry.data.get(CONF_FULL_THRESHOLD),
        humidity_on_threshold=entry.options.get(CONF_HUMIDITY_ON, entry.data.get(CONF_HUMIDITY_ON)),
        humidity_off_threshold=entry.options.get(CONF_HUMIDITY_OFF, entry.data.get(CONF_HUMIDITY_OFF)),
        start_time=entry.data.get(CONF_START_TIME),
        end_time=entry.data.get(CONF_END_TIME),
    )

    coordinator = DehumidifierCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok