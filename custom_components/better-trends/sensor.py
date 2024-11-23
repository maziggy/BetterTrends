from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

# Platform setup function
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data["entities"]  # Get user-configured entities
    interval = DEFAULT_INTERVAL  # Default collection interval
    trend_values = DEFAULT_TREND_VALUES  # Default number of steps for trend calculation

    # Create sensors for the user-defined entities
    trend_sensors = [
        BetterTrendsSensor(entity_id, trend_values, interval) for entity_id in user_entities
    ]

    # Add static sensors for interval and steps
    trend_sensors.append(TrendIntervalSensor(interval))
    trend_sensors.append(TrendStepsSensor(trend_values))

    # Add all the sensors to Home Assistant
    async_add_entities(trend_sensors, update_before_add=True)


# Define the BetterTrendsSensor class for trend calculation
class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values, interval):
        self._entity_id = entity_id
        self._trend_values = trend_values
        self._interval = interval
        self._values = []
        self._last_fetched_value = None
        self._state = None
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start the periodic data collection."""
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        while True:
            try:
                state = self.hass.states.get(self._entity_id)
                if state is not None:
                    try:
                        value = float(state.state)
                        self._handle_new_value(value)
                    except ValueError:
                        _LOGGER.warning(f"Invalid state for {self._entity_id}: {state.state}")
                        self._state = None
                else:
                    _LOGGER.warning(f"Entity {self._entity_id} not found.")
                    self._state = None
            except Exception as e:
                _LOGGER.error(f"Error collecting data for {self._entity_id}: {e}")
                self._state = None

            self.async_write_ha_state()  # Notify Home Assistant of state change
            await asyncio.sleep(self._interval)

    def _handle_new_value(self, value):
        """Handle new value and calculate the trend."""
        if not self._values:
            if self._last_fetched_value is not None:
                self._state = round(self._last_fetched_value - value, 1)
                _LOGGER.info(f"Initial trend for {self._entity_id}: {self._state}")
            self._last_fetched_value = value
        else:
            self._add_value(value)
            if len(self._values) == self._trend_values:
                self._state = self._calculate_trend()

    def _add_value(self, value):
        """Add a value to the rolling buffer."""
        if len(self._values) >= self._trend_values:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / self._trend_values, 1)


# Define the static TrendIntervalSensor class
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


# Define the static TrendStepsSensor class
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
