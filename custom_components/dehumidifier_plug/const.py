DOMAIN = "dehumidifier_plug"

# Configuration keys
CONF_NAME = "name"
CONF_SWITCH = "switch_entity"
CONF_POWER = "power_sensor"
CONF_HUMIDITY = "humidity_sensor"
CONF_FULL_THRESHOLD = "full_power_threshold"
CONF_HUMIDITY_ON = "humidity_on_threshold"
CONF_HUMIDITY_OFF = "humidity_off_threshold"
CONF_START_TIME = "start_time"
CONF_END_TIME = "end_time"

# Default values for configuration
DEFAULT_FULL_THRESHOLD = 2.0  # Watts: below this is considered full
DEFAULT_HUMIDITY_ON = 60      # Percentage: start dehumidifying above this
DEFAULT_HUMIDITY_OFF = 50     # Percentage: stop dehumidifying below this
DEFAULT_START_TIME = "09:00:00"
DEFAULT_END_TIME = "20:00:00"

