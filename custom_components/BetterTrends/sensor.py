from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN, SENSOR_SUFFIX

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Better Trends sensors based on the configuration entry."""
    sensor_ids = config_entry.data.get("sensors", [])
    new_entities = []

    for sensor_id in sensor_ids:
        # Generate a unique suffix for each new sensor
        new_sensor_suffix = f"{sensor_id.split('.')[1]}{SENSOR_SUFFIX}"
        new_entities.append(BetterTrendsSensor(sensor_id, new_sensor_suffix))

    async_add_entities(new_entities, True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to track trends based on another sensor's state."""

    def __init__(self, original_sensor_id, unique_suffix):
        self._original_sensor_id = original_sensor_id
        self._attr_unique_id = unique_suffix
        self._attr_name = f"{original_sensor_id} Trend"
        self._state = None

    @property
    def unique_id(self):
        """Return a unique ID for this entity."""
        return self._attr_unique_id

    @property
    def state(self):
        return self._state

    async def async_update(self):
        """Fetch the latest data from the original sensor and calculate a trend."""
        original_state = self.hass.states.get(self._original_sensor_id)
        if original_state:
            # Example logic: copy the state directly (replace with trend calculation if needed)
            self._state = original_state.state
