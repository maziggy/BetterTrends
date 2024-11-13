from homeassistant.helpers.entity import Entity
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup BetterTrends sensor entities based on ConfigEntry options."""
    
    # Retrieve the list of sensors from ConfigEntry options
    sensor_names = entry.options.get("sensors", [
        "better_trends_interval",
        "better_trends_steps",
        "better_trends_steps_curr"
    ])

    # Define a list of sensor entities to be added
    sensors = [BetterTrendsSensor(name) for name in sensor_names]
    async_add_entities(sensors, update_before_add=True)

class BetterTrendsSensor(Entity):
    def __init__(self, name):
        """Initialize the BetterTrends sensor."""
        self._attr_name = name
        self._attr_state = None  # Set to None initially

    async def async_update(self):
        """Update the sensor state."""
        try:
            # Retrieve a simulated or calculated value
            self._attr_state = self.get_trend_value()
            _LOGGER.debug("Updated sensor %s state to %s", self._attr_name, self._attr_state)
        except Exception as e:
            _LOGGER.error("Error updating sensor %s: %s", self._attr_name, e)

    def get_trend_value(self):
        """Placeholder method to calculate or retrieve a value."""
        # Example: Return a simple placeholder value; replace with real logic as needed
        return 100  # Replace this with a real calculation or fetch
