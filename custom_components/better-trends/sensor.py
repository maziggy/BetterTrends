from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values, interval):
        self._entity_id = entity_id
        self._trend_values = trend_values  # Number of steps for trend calculation
        self._interval = interval  # Collection interval (seconds)
        self._values = []  # Rolling buffer to store collected states
        self._state = None
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start the periodic data collection when the sensor is added."""
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate trend."""
        while True:
            try:
                # Fetch the latest state from the monitored entity
                state = self.hass.states.get(self._entity_id)
                if state is not None:
                    try:
                        value = float(state.state)
                        self._add_value(value)
                        if len(self._values) == self._trend_values:
                            self._state = self._calculate_trend()
                            self.async_write_ha_state()  # Notify Home Assistant about state change
                    except ValueError:
                        _LOGGER.warning(f"Invalid state for {self._entity_id}: {state.state}")
                else:
                    _LOGGER.warning(f"Entity {self._entity_id} not found.")
            except Exception as e:
                _LOGGER.error(f"Error collecting data for {self._entity_id}: {e}")

            # Wait for the next collection interval
            await asyncio.sleep(self._interval)

    def _add_value(self, value):
        """Add a new value to the rolling buffer."""
        if len(self._values) >= self._trend_values:
            self._values.pop(0)  # Remove the oldest value
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on collected values."""
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
