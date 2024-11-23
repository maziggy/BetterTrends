from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors."""
    # Get user-provided entities from the config
    user_entities = entry.data["entities"]

    # Create sensors for user entities
    trend_sensors = [BetterTrendsSensor(entity_id) for entity_id in user_entities]

    # Add the additional auto-created sensors
    trend_sensors.append(TrendIntervalSensor(DEFAULT_INTERVAL))
    trend_sensors.append(TrendStepsSensor(DEFAULT_TREND_VALUES))

    # Add all sensors
    async_add_entities(trend_sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id):
        self._entity_id = entity_id
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"
        self._state = None

    @property
    def native_value(self):
        """Return the current state."""
        return self._state

    async def async_update(self):
        """Fetch the latest state from the monitored entity."""
        state = self.hass.states.get(self._entity_id)
        if state is not None:
            self._state = float(state.state)  # Convert state to a float for trend calculation


class TrendIntervalSensor(SensorEntity):
    """A sensor to represent the trend interval."""

    def __init__(self, default_interval):
        self._attr_name = "Trend Sensor Interval"
        self._attr_unique_id = "trend_sensor_interval"
        self._state = default_interval

    @property
    def native_value(self):
        """Return the current interval value."""
        return self._state

    async def async_update(self):
        """Update the interval sensor if necessary."""
        # No real updates required for this static sensor in this example.
        pass


class TrendStepsSensor(SensorEntity):
    """A sensor to represent the number of trend steps."""

    def __init__(self, default_steps):
        self._attr_name = "Trend Sensor Steps"
        self._attr_unique_id = "trend_sensor_steps"
        self._state = default_steps

    @property
    def native_value(self):
        """Return the current trend steps value."""
        return self._state

    async def async_update(self):
        """Update the steps sensor if necessary."""
        # No real updates required for this static sensor in this example.
        pass
