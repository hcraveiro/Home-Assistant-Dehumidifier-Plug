"""Dehumidifier configuration, including legacy migration."""
from dataclasses import dataclass
from datetime import time

from .const import (
    CONF_WEEKDAYS, DEFAULT_WEEKDAYS, CONF_TIME_WINDOWS,
    CONF_START_TIME, CONF_END_TIME, DEFAULT_START_TIME, DEFAULT_END_TIME,
    CONF_FULL_THRESHOLD, CONF_HUMIDITY_ON, CONF_HUMIDITY_OFF,
    DEFAULT_FULL_THRESHOLD, DEFAULT_HUMIDITY_ON, DEFAULT_HUMIDITY_OFF,
)


def merge_entry_settings(data: dict, options: dict) -> dict:
    """Null options must never remove a configured entity reference."""
    return {**data, **{key: value for key, value in options.items() if value is not None}}


def parse_time(value: str | time) -> time:
    """Parse both legacy and current Home Assistant time values."""
    return value if isinstance(value, time) else time.fromisoformat(value)


@dataclass
class DehumidifierConfig:
    name: str
    switch_entity: str
    power_sensor: str
    humidity_sensor: str
    full_power_threshold: float
    humidity_on_threshold: float
    humidity_off_threshold: float
    weekdays: list[str]
    time_windows: list[tuple[time, time]]

    @staticmethod
    def from_dict(data: dict) -> "DehumidifierConfig":
        windows = data.get(CONF_TIME_WINDOWS)
        if windows is None:
            windows = [{
                "start": data.get(CONF_START_TIME, DEFAULT_START_TIME),
                "end": data.get(CONF_END_TIME, DEFAULT_END_TIME),
            }]
        return DehumidifierConfig(
            name=data["name"],
            switch_entity=data["switch_entity"],
            power_sensor=data["power_sensor"],
            humidity_sensor=data["humidity_sensor"],
            full_power_threshold=float(data.get(CONF_FULL_THRESHOLD, DEFAULT_FULL_THRESHOLD)),
            humidity_on_threshold=float(data.get(CONF_HUMIDITY_ON, DEFAULT_HUMIDITY_ON)),
            humidity_off_threshold=float(data.get(CONF_HUMIDITY_OFF, DEFAULT_HUMIDITY_OFF)),
            weekdays=data.get(CONF_WEEKDAYS, DEFAULT_WEEKDAYS),
            time_windows=[(parse_time(w["start"]), parse_time(w["end"])) for w in windows],
        )
