from homeassistant.helpers.entity import Entity

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup BetterTrends sensor entities based on ConfigEntry options."""
    
    # Retrieve the list of sensors from ConfigEntry options or initialize default sensors
    sensor_names = entry.options.get("sensors", [
        "better_trends_interval",
        "better_trends_steps",
        "better_trends_steps_curr"
    ])

    # Define a list of sensor entities to be added
    sensors = [BetterTrendsSensor(sensor_name) for sensor_name in sensor_names]

    async_add_entities(sensors, update_before_add=True)

class BetterTrendsSensor(Entity):
    def __init__(self, name):
        """Initialize the BetterTrends sensor."""
        self._attr_name = name
        self._attr_state = 0  # Initial state

    async def async_update(self):
        """Update the sensor state."""
        # Basic increment logic for state; adjust this with actual data logic
        self._attr_state += 1
