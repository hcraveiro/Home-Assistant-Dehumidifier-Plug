from dataclasses import dataclass

@dataclass
class DehumidifierConfig:
    name: str
    switch_entity: str
    power_sensor: str
    humidity_sensor: str
    full_power_threshold: float
    humidity_on_threshold: float
    humidity_off_threshold: float
    start_time: str
    end_time: str
