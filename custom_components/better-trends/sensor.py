from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors."""
    # Get user-provided entities and default values
    user_entities = entry.data["entities"]
    interval = DEFAULT_INTERVAL
    trend_values = DEFAULT_TREND_VALUES

    # Create sensors for user-provided entities with trend calculation
    trend_sensors = [
        BetterTrendsSensor(entity_id, trend_values, interval) for entity_id in user_entities
    ]

    # Add the additional auto-created sensors
    trend_sensors.append(TrendIntervalSensor(interval))
    trend_sensors.append(TrendStepsSensor(trend_values))

    # Add all sensors
    async_add_entities(trend_sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values, interval):
        self._entity_id = entity_id
        self._trend_values = trend_values  # Number of steps for trend calculation
        self._interval = interval  # Collection interval (seconds)
        self._values = []  # Rolling buffer to store collected states
        self._last_fetched_value = None  # Store last fetched value for startup case
        self._state = None  # Trend calculation result
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start the periodic data collection when the sensor is added."""
        # Start data collection in the background
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate trend."""
        while True:
            try:
                # Fetch the latest state from the monitored entity
                state = self.hass.states.get(self._entity_id)
                if state is not None:
                    try:
                        value = float(state.state)  # Convert state to float
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

            # Notify Home Assistant of state change
            self.async_write_ha_state()

            # Wait for the next collection interval
            await asyncio.sleep(self._interval)

    def _handle_new_value(self, value):
        """Handle a newly fetched value and calculate the trend."""
        if not self._values:
            # If the rolling buffer is empty (e.g., after restart)
            if self._last_fetched_value is not None:
                # Calculate <old value> - <new value>
                self._state = round(self._last_fetched_value - value, 1)
                _LOGGER.info(f"Initial trend for {self._entity_id}: {self._state}")
            # Store the first value for future calculations
            self._last_fetched_value = value
        else:
            # Add the new value to the rolling buffer
            self._add_value(value)
            if len(self._values) == self._trend_values:
                # Calculate the trend when buffer is full
                self._state = self._calculate_trend()

    def _add_value(self, value):
        """Add a new value to the rolling buffer."""
        if len(self._values) >= self._trend_values:
            self._values.pop(0)  # Remove the oldest value
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        trend = round(total / self._trend_values, 1)
        _LOGGER.debug(f"Calculated trend for {self._entity_id}: {trend}")
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
