from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    # Create trend sensors for user-provided entities
    trend_sensors = [
        BetterTrendsSensor(entity_id, hass, entry)
        for entity_id in user_entities
    ]
    async_add_entities(trend_sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, hass, entry: ConfigEntry):
        self._entity_id = entity_id
        self.hass = hass
        self._values = []
        self._state = None
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"
        self._interval_entity = "number.trend_sensor_interval"
        self._steps_entity = "number.trend_sensor_steps"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start periodic data collection when the sensor is added."""
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        current_step_entity = "number.trend_sensor_current_step"  # Replace with your actual entity ID

        while True:
            try:
                # Fetch interval from the number entity
                interval_state = self.hass.states.get(self._interval_entity)
                interval = int(interval_state.state) if interval_state and interval_state.state.isdigit() else 60

                state = self.hass.states.get(self._entity_id)
                if state:
                    try:
                        value = float(state.state)
                        self._handle_new_value(value)

                        # Update the current step entity dynamically
                        steps_state = self.hass.states.get(self._steps_entity)
                        steps = int(steps_state.state) if steps_state and steps_state.state.isdigit() else 10
                        current_step = min(len(self._values), steps)

                        self.hass.states.async_set(current_step_entity, current_step, {})
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
            await asyncio.sleep(interval)
                        
    def _handle_new_value(self, value):
        """Handle a new value and calculate the trend."""
        if not self._values:
            self._state = 0.0
        else:
            self._add_value(value)
            self._state = self._calculate_trend()

    def _add_value(self, value):
        """Maintain a fixed-length buffer."""
        # Fetch steps from the number entity
        steps_state = self.hass.states.get(self._steps_entity)
        steps = int(steps_state.state) if steps_state and steps_state.state.isdigit() else 10

        if len(self._values) >= steps:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / len(self._values), 2)
