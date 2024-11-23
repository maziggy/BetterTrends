from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("SensorEntity successfully imported and sensor.py loaded.")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    # Create trend sensors for user-configured entities
    sensors = [BetterTrendsSensor(entity_id, DEFAULT_TREND_VALUES, DEFAULT_INTERVAL, hass) for entity_id in user_entities]

    # Add hard-coded interval and steps sensors
    sensors.append(HardCodedSensor("Trend Sensor Interval", "trend_sensor_interval", DEFAULT_INTERVAL))
    sensors.append(HardCodedSensor("Trend Sensor Steps", "trend_sensor_steps", DEFAULT_TREND_VALUES))

    async_add_entities(sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values, interval, hass):
        self._entity_id = entity_id
        self._trend_values = trend_values
        self._interval = interval
        self._values = []
        self._state = None
        self.hass = hass
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start collecting data."""
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        while True:
            try:
                state = self.hass.states.get(self._entity_id)
                if state:
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

            self.async_write_ha_state()
            await asyncio.sleep(self._interval)

    def _handle_new_value(self, value):
        """Handle new value and calculate the trend."""
        if not self._values:
            self._state = 0.0  # Initialize trend to 0
        else:
            self._add_value(value)
            if len(self._values) == self._trend_values:
                self._state = self._calculate_trend()
        self._values.append(value)

    def _add_value(self, value):
        """Maintain a fixed-length buffer."""
        if len(self._values) >= self._trend_values:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / self._trend_values, 2)


class HardCodedSensor(SensorEntity):
    """A hard-coded sensor for interval and steps."""

    def __init__(self, name, unique_id, initial_value):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._state = initial_value

    @property
    def native_value(self):
        """Return the hard-coded sensor state."""
        return self._state

    def update_value(self, new_value):
        """Update the state of the hard-coded sensor."""
        self._state = new_value
        self.async_write_ha_state()
