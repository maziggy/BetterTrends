from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    # Ensure input_number helpers are created for interval and steps
    await _ensure_input_number(hass, "input_number.trend_sensor_interval", "Trend Sensor Interval", 1, 3600, DEFAULT_INTERVAL)
    await _ensure_input_number(hass, "input_number.trend_sensor_steps", "Trend Sensor Steps", 1, 100, DEFAULT_TREND_VALUES)

    # Create sensors for user-defined entities
    sensors = [BetterTrendsSensor(entity_id, hass) for entity_id in user_entities]

    async_add_entities(sensors, update_before_add=True)


async def _ensure_input_number(hass, entity_id, name, min_value, max_value, initial_value):
    """Ensure an input_number entity exists."""
    if not hass.states.get(entity_id):
        try:
            _LOGGER.info(f"Creating {entity_id} as input_number.")
            await hass.services.async_call(
                "input_number",
                "create",
                {
                    "entity_id": entity_id,
                    "name": name,
                    "min": min_value,
                    "max": max_value,
                    "step": 1,
                    "initial": initial_value,
                },
            )
        except Exception as e:
            _LOGGER.error(f"Failed to create {entity_id}: {e}")


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, hass):
        self._entity_id = entity_id
        self._values = []
        self._state = None
        self.hass = hass
        self._interval = DEFAULT_INTERVAL  # Default interval
        self._trend_values = DEFAULT_TREND_VALUES  # Default steps
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start listening for state changes and periodically collect data."""
        self.hass.loop.create_task(self._collect_data())
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_input_number_change)

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

    @callback
    def _handle_input_number_change(self, event):
        """React to changes in input_number for interval and steps."""
        if event.data.get("entity_id") == "input_number.trend_sensor_interval":
            self._update_interval()
        elif event.data.get("entity_id") == "input_number.trend_sensor_steps":
            self._update_steps()

    def _update_interval(self):
        """Update the interval from input_number."""
        state = self.hass.states.get("input_number.trend_sensor_interval")
        if state:
            try:
                self._interval = int(float(state.state))
                _LOGGER.info(f"Updated interval to {self._interval}")
            except ValueError:
                _LOGGER.warning(f"Invalid interval value: {state.state}")

    def _update_steps(self):
        """Update the steps from input_number."""
        state = self.hass.states.get("input_number.trend_sensor_steps")
        if state:
            try:
                self._trend_values = int(float(state.state))
                _LOGGER.info(f"Updated steps to {self._trend_values}")
            except ValueError:
                _LOGGER.warning(f"Invalid steps value: {state.state}")

    def _handle_new_value(self, value):
        """Handle new value and calculate the trend."""
        if not self._values:
            self._state = 0.0
        else:
            self._add_value(value)
            if len(self._values) == self._trend_values:
                self._state = self._calculate_trend()

    def _add_value(self, value):
        """Maintain a fixed-length buffer."""
        if len(self._values) >= self._trend_values:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / self._trend_values, 2)
