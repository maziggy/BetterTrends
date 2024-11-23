from homeassistant.helpers.event import async_track_state_change
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
        self._interval = 60  # Default interval
        self._steps = 10  # Default steps
        self._unsub_listeners = []  # List to store unsub functions for state listeners

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start periodic data collection and listen for changes in interval/steps."""
        self._update_interval_and_steps()

        # Listen for state changes to interval and steps
        self._unsub_listeners.append(
            async_track_state_change(
                self.hass, self._interval_entity, self._handle_interval_change
            )
        )
        self._unsub_listeners.append(
            async_track_state_change(
                self.hass, self._steps_entity, self._handle_steps_change
            )
        )

        # Start periodic data collection
        self.hass.loop.create_task(self._collect_data())

    async def async_will_remove_from_hass(self):
        """Clean up state listeners when the entity is removed."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    def _update_interval_and_steps(self):
        """Fetch the current interval and steps from the number entities."""
        interval_state = self.hass.states.get(self._interval_entity)
        self._interval = int(interval_state.state) if interval_state and interval_state.state.isdigit() else 60

        steps_state = self.hass.states.get(self._steps_entity)
        self._steps = int(steps_state.state) if steps_state and steps_state.state.isdigit() else 10

    async def _handle_interval_change(self, entity_id, old_state, new_state):
        """Handle changes to the interval entity."""
        if new_state and new_state.state.isdigit():
            self._interval = int(new_state.state)
            _LOGGER.info(f"Updated interval to {self._interval} seconds for {self._attr_name}")

    async def _handle_steps_change(self, entity_id, old_state, new_state):
        """Handle changes to the steps entity."""
        if new_state and new_state.state.isdigit():
            self._steps = int(new_state.state)
            _LOGGER.info(f"Updated steps to {self._steps} for {self._attr_name}")

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        current_step_entity = "number.trend_sensor_current_step"  # Hardcoded entity ID

        while True:
            try:
                state = self.hass.states.get(self._entity_id)
                if state:
                    try:
                        value = float(state.state)
                        self._add_value(value)

                        # Dynamically update the current step entity
                        current_step = len(self._values)
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
            await asyncio.sleep(self._interval)

    def _add_value(self, value):
        """Maintain a fixed-length buffer and calculate trend when steps are reached."""
        self._values.append(value)

        # Check if we have enough values to calculate the trend
        if len(self._values) >= self._steps:
            self._state = self._calculate_trend()
            self._values = []  # Reset the buffer after trend calculation

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / len(self._values), 2)
