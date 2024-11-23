from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES

class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values):
        self._entity_id = entity_id
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"
        self._state = None
        self._trend_values = trend_values
        self._value_history = [0.0] * trend_values  # Initialize rolling history with zeros

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_update(self):
        """Fetch the latest state from the monitored entity and calculate the trend."""
        state = self.hass.states.get(self._entity_id)
        if state is not None:
            try:
                # Get the latest value from the monitored entity
                latest_value = float(state.state)

                # Update the rolling history
                self._value_history.pop(0)  # Remove the oldest value
                self._value_history.append(latest_value)  # Add the newest value

                # Calculate the trend using your logic
                self._state = self._calculate_trend(latest_value, self._value_history)
            except ValueError:
                # Handle cases where the entity's state is not a valid float
                self._state = None

    def _calculate_trend(self, last, history):
        """Calculate the trend based on the last value and rolling history."""
        # Sum the values in the history (excluding the most recent one)
        summed_values = sum(history[:-1])
        trend = round(last - (summed_values / len(history[:-1])), 2)
        return trend


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors."""
    # Get user-provided entities and default values
    user_entities = entry.data["entities"]
    interval = DEFAULT_INTERVAL
    trend_values = DEFAULT_TREND_VALUES

    # Create sensors for user-provided entities with trend calculation
    trend_sensors = [
        BetterTrendsSensor(entity_id, trend_values) for entity_id in user_entities
    ]

    # Add the additional auto-created sensors
    trend_sensors.append(TrendIntervalSensor(interval))
    trend_sensors.append(TrendStepsSensor(trend_values))

    # Add all sensors
    async_add_entities(trend_sensors, update_before_add=True)
