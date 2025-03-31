from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from homeassistant.helpers.storage import Store
import logging

from .const import *
from .models import DehumidifierConfig
from .utils import slugify

_LOGGER = logging.getLogger(__name__)

class DehumidifierCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: DehumidifierConfig):
        self.hass = hass
        self.config = config
        self.storage = Store(hass, 1, f"{DOMAIN}_{slugify(config.name)}")
        self._last_auto_on = None
        self._power_low_since = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"DehumidifierCoordinator_{config.name}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

        hass.loop.create_task(self.load_persistent_data())

    async def _async_update_data(self):
        try:
            state_switch = self.hass.states.get(self.config.switch_entity)
            state_power = self.hass.states.get(self.config.power_sensor)
            state_humidity = self.hass.states.get(self.config.humidity_sensor)

            if not state_switch or not state_power or not state_humidity:
                raise UpdateFailed("Missing one or more entity states")

            if state_power.state in ("unavailable", "unknown") or state_humidity.state in ("unavailable", "unknown"):
                raise UpdateFailed("Power or humidity sensor is unavailable")

            auto_switch_id = f"switch.{slugify(f'{self.config.name}_control')}"
            state_auto = self.hass.states.get(auto_switch_id)
            auto_enabled = state_auto and state_auto.state == "on"

            is_on = state_switch.state == "on"
            power = float(state_power.state)
            humidity = float(state_humidity.state)

            now = datetime.now().time()
            start = datetime.strptime(self.config.start_time, "%H:%M:%S").time()
            end = datetime.strptime(self.config.end_time, "%H:%M:%S").time()

            inside_schedule = start <= now <= end if start < end else now >= start or now <= end
            humidity_low = humidity < self.config.humidity_off_threshold
            humidity_high = humidity > self.config.humidity_on_threshold

            if is_on and power < self.config.full_power_threshold:
                if not self._power_low_since:
                    self._power_low_since = datetime.now()
                    await self.save_persistent_data()
            else:
                if self._power_low_since:
                    self._power_low_since = None
                    await self.save_persistent_data()

            is_full = False
            if self._power_low_since:
                elapsed = datetime.now() - self._power_low_since
                if elapsed >= timedelta(seconds=60):
                    is_full = True

            _LOGGER.debug(
                f"{self.config.name} - Conditions: auto_enabled={auto_enabled}, inside_schedule={inside_schedule}, "
                f"is_on={is_on}, humidity_low={humidity_low}, humidity_high={humidity_high}, is_full={is_full}"
            )

            if auto_enabled and inside_schedule:
                if humidity_high and not is_full and not is_on:
                    _LOGGER.info(f"{self.config.name} - Turning on dehumidifier...")
                    await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.config.switch_entity}, blocking=True)
                    self._last_auto_on = datetime.now()
                    await self.save_persistent_data()
                elif humidity_low and is_on:
                    _LOGGER.info(f"{self.config.name} - Humidity below threshold. Turning off dehumidifier...")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
            elif auto_enabled and not inside_schedule and is_on:
                manual_override = False
                if self._last_auto_on:
                    manual_override = state_switch.last_changed > self._last_auto_on
                if humidity_low:
                    _LOGGER.info(f"{self.config.name} - Outside schedule and humidity low. Turning off dehumidifier...")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                elif manual_override:
                    _LOGGER.debug(f"{self.config.name} - Outside schedule. Manually turned on. Leaving dehumidifier on.")
                else:
                    _LOGGER.info(f"{self.config.name} - Outside schedule. Turning off dehumidifier...")
                    await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)

            _LOGGER.debug("%s - Dehumidifier data: is_on=%s, power=%.2f, humidity=%.2f, inside_schedule=%s, "
                "humidity_low=%s, humidity_high=%s, is_full=%s",
                self.config.name, is_on, power, humidity, inside_schedule, humidity_low, humidity_high, is_full
            )

            return {
               "is_on": is_on,
               "is_full": is_full,
               "inside_schedule": inside_schedule,
               "humidity_low": humidity_low
            }

        except Exception as e:
            raise UpdateFailed(f"Error updating dehumidifier data: {e}")

    async def load_persistent_data(self):
        data = await self.storage.async_load()
        if data:
            if "last_auto_on" in data:
                self._last_auto_on = datetime.fromisoformat(data["last_auto_on"])
            if "power_low_since" in data:
                self._power_low_since = datetime.fromisoformat(data["power_low_since"])

    async def save_persistent_data(self):
        await self.storage.async_save({
            "last_auto_on": self._last_auto_on.isoformat() if self._last_auto_on else None,
            "power_low_since": self._power_low_since.isoformat() if self._power_low_since else None
        })