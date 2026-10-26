"""Configuration and options forms for dehumidifier plugs."""
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    DOMAIN, CONF_NAME, CONF_SWITCH, CONF_POWER, CONF_HUMIDITY,
    CONF_FULL_THRESHOLD, CONF_HUMIDITY_ON, CONF_HUMIDITY_OFF,
    CONF_START_TIME, CONF_END_TIME, CONF_WEEKDAYS, CONF_TIME_WINDOWS,
    DEFAULT_FULL_THRESHOLD, DEFAULT_HUMIDITY_ON, DEFAULT_HUMIDITY_OFF,
    DEFAULT_START_TIME, DEFAULT_END_TIME, DEFAULT_WEEKDAYS,
)

WEEKDAY_SELECTOR = selector.SelectSelector(selector.SelectSelectorConfig(
    options=[selector.SelectOptionDict(value=value, label=label) for value, label in [
        ("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"),
        ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"), ("sun", "Sunday"),
    ]],
    multiple=True,
    mode=selector.SelectSelectorMode.DROPDOWN,
))
WINDOWS_SELECTOR = selector.ObjectSelector(selector.ObjectSelectorConfig(
    multiple=True,
    label_field="start",
    description_field="end",
    fields={
        "start": {"label": "Start time", "selector": selector.TimeSelector(), "required": True},
        "end": {"label": "End time", "selector": selector.TimeSelector(), "required": True},
    },
))


def schedule_fields(data):
    """Keep legacy start/end as the initial editor interval."""
    windows = data.get(CONF_TIME_WINDOWS)
    if windows is None:
        windows = [{
            "start": data.get(CONF_START_TIME, DEFAULT_START_TIME),
            "end": data.get(CONF_END_TIME, DEFAULT_END_TIME),
        }]
    return {
        vol.Required(CONF_WEEKDAYS, default=data.get(CONF_WEEKDAYS, DEFAULT_WEEKDAYS)): WEEKDAY_SELECTOR,
        vol.Required(CONF_TIME_WINDOWS, default=windows): WINDOWS_SELECTOR,
    }


def valid_schedule(data):
    """Reject empty or incomplete interval lists."""
    windows = data.get(CONF_TIME_WINDOWS, [])
    return bool(windows) and all(
        isinstance(window, dict) and bool(window.get("start")) and bool(window.get("end"))
        for window in windows
    )


def entity_field(key, data, domain):
    """Allow recovering legacy entries with missing entity IDs."""
    entity = selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))
    value = data.get(key)
    if value:
        return {vol.Required(key, default=value): entity}
    return {vol.Required(key): entity}


def threshold_fields(data):
    """Expose the same threshold settings in setup and options."""
    return {
        vol.Required(CONF_FULL_THRESHOLD, default=data.get(CONF_FULL_THRESHOLD, DEFAULT_FULL_THRESHOLD)):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=0, max=100, step=0.1, mode=selector.NumberSelectorMode.BOX)),
        vol.Required(CONF_HUMIDITY_ON, default=data.get(CONF_HUMIDITY_ON, DEFAULT_HUMIDITY_ON)):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)),
        vol.Required(CONF_HUMIDITY_OFF, default=data.get(CONF_HUMIDITY_OFF, DEFAULT_HUMIDITY_OFF)):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)),
    }


class DehumidifierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DehumidifierOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None and valid_schedule(user_input):
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            errors={"base": "invalid_schedule"} if user_input is not None else {},
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): selector.TextSelector(),
                **entity_field(CONF_SWITCH, user_input or {}, "switch"),
                **entity_field(CONF_POWER, user_input or {}, "sensor"),
                **entity_field(CONF_HUMIDITY, user_input or {}, "sensor"),
                **threshold_fields(user_input or {}),
                **schedule_fields(user_input or {}),
            }),
        )


class DehumidifierOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None and valid_schedule(user_input):
            return self.async_create_entry(title="", data=user_input)

        data = {
            **self._config_entry.data,
            **{key: value for key, value in self._config_entry.options.items() if value is not None},
            **(user_input or {}),
        }
        return self.async_show_form(
            step_id="init",
            errors={"base": "invalid_schedule"} if user_input is not None else {},
            data_schema=vol.Schema({
                **entity_field(CONF_SWITCH, data, "switch"),
                **entity_field(CONF_POWER, data, "sensor"),
                **entity_field(CONF_HUMIDITY, data, "sensor"),
                **threshold_fields(data),
                **schedule_fields(data),
            }),
        )
