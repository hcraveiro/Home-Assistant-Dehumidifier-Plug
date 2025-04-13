from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_component import DEFAULT_SCAN_INTERVAL
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
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
        self._manual_override = False
        self._last_switch_state = None
        self._auto_turning_on = False
        self._is_full_latched = False

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
            _LOGGER.debug(f"{self.config.name} - Found auto switch entity: {auto_switch_id} with state: {state_auto.state if state_auto else 'Not found'}")

            is_on = state_switch.state == "on"
            power = float(state_power.state)
            humidity = float(state_humidity.state)

            now_local = dt_util.now()
            now_utc = dt_util.utcnow()
            now = now_local.time()

            start = self.config.start_time
            end = self.config.end_time
            # Schedule handles cross-midnight periods
            inside_schedule = start <= now <= end if start < end else now >= start or now <= end

            humidity_low = humidity < self.config.humidity_off_threshold
            humidity_high = humidity > self.config.humidity_on_threshold

            # Manual override detection
            previous_state = self._last_switch_state
            self._last_switch_state = state_switch.state

            if previous_state is not None and previous_state != state_switch.state:
                if state_switch.state == "on" and not self._auto_turning_on:
                    self._manual_override = True
                    _LOGGER.debug(f"{self.config.name} - Manual override detected: switch turned on manually.")
                elif state_switch.state == "off":
                    self._manual_override = False
                    _LOGGER.debug(f"{self.config.name} - Switch turned off. Clearing manual override.")
                await self.save_persistent_data()

            # Full detection logic and latching
            is_full = False
            if is_on and power < self.config.full_power_threshold:
                if not self._power_low_since:
                    self._power_low_since = now_utc
                    _LOGGER.debug(f"{self.config.name} - Power dropped below threshold. Starting full timer...")
                    await self.save_persistent_data()
            else:
                if self._power_low_since:
                    _LOGGER.debug(f"{self.config.name} - Power no longer low. Clearing full timer.")
                self._power_low_since = None
                await self.save_persistent_data()
                if self._is_full_latched:
                    _LOGGER.debug(f"{self.config.name} - Tank no longer full. Clearing latched full state.")
                    self._is_full_latched = False
                    await self.save_persistent_data()

            if self._power_low_since:
                elapsed = now_utc - self._power_low_since
                if elapsed >= timedelta(seconds=60):
                    is_full = True
                    if not self._is_full_latched:
                        _LOGGER.debug(f"{self.config.name} - Power has been low for {elapsed}. Marking as full and latching.")
                        self._is_full_latched = True
                        await self.save_persistent_data()
                else:
                    _LOGGER.debug(f"{self.config.name} - Power low for {elapsed.total_seconds():.0f}s but threshold not yet met.")

            if self._is_full_latched:
                is_full = True

            _LOGGER.debug(
                f"{self.config.name} - Conditions: auto_enabled={auto_enabled}, inside_schedule={inside_schedule}, "
                f"is_on={is_on}, humidity_low={humidity_low}, humidity_high={humidity_high}, "
                f"is_full={is_full}, manual_override={self._manual_override}"
            )

            # Automatic control logic
            if auto_enabled:
                self._auto_turning_on = False
                if inside_schedule:
                    if humidity_high and not is_full and not is_on:
                        _LOGGER.info(f"{self.config.name} - Turning on dehumidifier...")
                        self._auto_turning_on = True
                        await self.hass.services.async_call("switch", "turn_on", {"entity_id": self.config.switch_entity}, blocking=True)
                        self._last_auto_on = now_utc
                        self._manual_override = False
                        await self.save_persistent_data()
                    elif humidity_low and is_on:
                        _LOGGER.info(f"{self.config.name} - Humidity below threshold. Turning off dehumidifier...")
                        await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                        self._manual_override = False
                        await self.save_persistent_data()
                else:
                    if is_on:
                        if humidity_low:
                            _LOGGER.info(f"{self.config.name} - Outside schedule and humidity low. Turning off dehumidifier...")
                            await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)
                            self._manual_override = False
                            await self.save_persistent_data()
                        elif self._manual_override:
                            _LOGGER.debug(f"{self.config.name} - Outside schedule. Manually turned on. Leaving dehumidifier on.")
                        elif is_full:
                            _LOGGER.debug(f"{self.config.name} - Outside schedule and latched full. Leaving dehumidifier on.")
                        else:
                            _LOGGER.info(f"{self.config.name} - Outside schedule. Turning off dehumidifier...")
                            await self.hass.services.async_call("switch", "turn_off", {"entity_id": self.config.switch_entity}, blocking=True)

            _LOGGER.debug(
                f"{self.config.name} - Dehumidifier data: is_on={is_on}, power={power:.2f}, humidity={humidity:.2f}, "
                f"inside_schedule={inside_schedule}, humidity_low={humidity_low}, humidity_high={humidity_high}, "
                f"is_full={is_full}"
            )

            return {
                "is_on": is_on,
                "is_full": is_full,
                "inside_schedule": inside_schedule,
                "humidity_low": humidity_low,
                "humidity_high": humidity_high,
                "manual_override": self._manual_override,
            }

        except Exception as e:
            raise UpdateFailed(f"Error updating dehumidifier data: {e}")

    async def load_persistent_data(self):
        data = await self.storage.async_load()
        if data:
            if "last_auto_on" in data:
                self._last_auto_on = dt_util.parse_datetime(data["last_auto_on"])
            if "power_low_since" in data:
                self._power_low_since = dt_util.parse_datetime(data["power_low_since"])
            self._manual_override = data.get("manual_override", False)
            self._last_switch_state = data.get("last_switch_state", None)
            self._is_full_latched = data.get("is_full_latched", False)

    async def save_persistent_data(self):
        await self.storage.async_save({
            "last_auto_on": self._last_auto_on.isoformat() if self._last_auto_on else None,
            "power_low_since": self._power_low_since.isoformat() if self._power_low_since else None,
            "manual_override": self._manual_override,
            "last_switch_state": self._last_switch_state,
            "is_full_latched": self._is_full_latched,
        })

