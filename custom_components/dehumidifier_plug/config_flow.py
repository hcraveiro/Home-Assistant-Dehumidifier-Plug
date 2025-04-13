from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    DOMAIN, CONF_NAME, CONF_SWITCH, CONF_POWER, CONF_HUMIDITY,
    CONF_FULL_THRESHOLD, CONF_HUMIDITY_ON, CONF_HUMIDITY_OFF,
    CONF_START_TIME, CONF_END_TIME,
    DEFAULT_FULL_THRESHOLD, DEFAULT_HUMIDITY_ON, DEFAULT_HUMIDITY_OFF,
    DEFAULT_START_TIME, DEFAULT_END_TIME,
)

class DehumidifierConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DehumidifierOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input
            )

        # Display the setup form with default values and selectors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): selector.TextSelector(),
                vol.Required(CONF_SWITCH): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="switch")
                ),
                vol.Required(CONF_POWER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Required(CONF_HUMIDITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_FULL_THRESHOLD, default=DEFAULT_FULL_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=0.1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_HUMIDITY_ON, default=DEFAULT_HUMIDITY_ON): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_HUMIDITY_OFF, default=DEFAULT_HUMIDITY_OFF): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_START_TIME, default=DEFAULT_START_TIME): selector.TimeSelector(),
                vol.Optional(CONF_END_TIME, default=DEFAULT_END_TIME): selector.TimeSelector(),
            })
        )

class DehumidifierOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Display the options form for editing thresholds and time range
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_HUMIDITY_ON,
                    default=self.config_entry.options.get(CONF_HUMIDITY_ON, DEFAULT_HUMIDITY_ON)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_HUMIDITY_OFF,
                    default=self.config_entry.options.get(CONF_HUMIDITY_OFF, DEFAULT_HUMIDITY_OFF)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=100, step=1, unit_of_measurement="%", mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_START_TIME,
                    default=self.config_entry.options.get(CONF_START_TIME, DEFAULT_START_TIME)
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_END_TIME,
                    default=self.config_entry.options.get(CONF_END_TIME, DEFAULT_END_TIME)
                ): selector.TimeSelector(),
            })
        )

