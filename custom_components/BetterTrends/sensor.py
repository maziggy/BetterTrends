from homeassistant.helpers.entity import Entity

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup BetterTrends sensor entities based on ConfigEntry options."""

    sensors = []
    
    # Retrieve the list of sensors from ConfigEntry options or initialize default sensors
    sensor_names = entry.options.get("sensors", [
        "better_trends_interval",
        "better_trends_steps",
        "better_trends_steps_curr"
    ])

    for sensor_name in sensor_names:
        sensors.append(BetterTrendsSensor(sensor_name))

    async_add_entities(sensors, update_before_add=True)

class BetterTrendsSensor(Entity):
    def __init__(self, name):
        """Initialize the BetterTrends sensor."""
        self._name = name
        self._state = 0  # Initialize with a default value of 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    async def async_update(self):
        """Update the sensor state."""
        # Simple placeholder to confirm async_update runs without "not_implemented" errors
        self._state = self._state + 1 if isinstance(self._state, int) else 0
