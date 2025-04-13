from datetime import datetime, time
from dataclasses import dataclass

@dataclass
class DehumidifierConfig:
    """Stores configuration for a dehumidifier instance."""
    name: str
    switch_entity: str
    power_sensor: str
    humidity_sensor: str
    full_power_threshold: float
    humidity_on_threshold: float
    humidity_off_threshold: float
    start_time: time
    end_time: time

    @staticmethod
    def from_dict(data: dict) -> "DehumidifierConfig":
        """Creates a DehumidifierConfig object from a dictionary, converting time strings if needed."""

        def ensure_time(value):
            if isinstance(value, time):
                return value
            if isinstance(value, str):
                return datetime.strptime(value, "%H:%M:%S").time()
            raise ValueError("Invalid time format")

        return DehumidifierConfig(
            name=data["name"],
            switch_entity=data["switch_entity"],
            power_sensor=data["power_sensor"],
            humidity_sensor=data["humidity_sensor"],
            full_power_threshold=float(data["full_power_threshold"]),
            humidity_on_threshold=float(data["humidity_on_threshold"]),
            humidity_off_threshold=float(data["humidity_off_threshold"]),
            start_time=ensure_time(data["start_time"]),
            end_time=ensure_time(data["end_time"]),
        )
        
        