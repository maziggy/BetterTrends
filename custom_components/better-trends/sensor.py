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
        self._state = 0  # Default state to 0
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"
        self._interval_entity = "number.trend_sensor_interval"
        self._steps_entity = "number.trend_sensor_steps"
        self._interval = self.hass.states.get(self._interval_entity)
        self._steps = self.hass.states.get(self._steps_entity)
        self._unsub_listeners = []  # List to store unsub functions for state listeners
        self._current_step_entity = "number.trend_sensor_current_step"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start periodic data collection and initialize default states."""
        # Wait for number entities before initializing
        for _ in range(10):  # Retry for up to 10 seconds
            if self.hass.states.get(self._interval_entity) and self.hass.states.get(self._steps_entity):
                _LOGGER.info(f"Number entities found: {self._interval_entity}, {self._steps_entity}")
                break
            _LOGGER.warning(f"Waiting for {self._interval_entity} and {self._steps_entity} to become available...")
            await asyncio.sleep(1)

        # Log error if entities are still missing after retries
        if not self.hass.states.get(self._interval_entity) or not self.hass.states.get(self._steps_entity):
            _LOGGER.error(f"Number entities {self._interval_entity} and {self._steps_entity} not found after retries")
            return  # Exit to prevent further errors

        self._update_interval_and_steps()
        self.hass.loop.create_task(self._collect_data())

    async def async_will_remove_from_hass(self):
        """Clean up state listeners when the entity is removed."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    def _update_interval_and_steps(self):
        """Fetch the current interval and steps from the number entities."""
        _LOGGER.info("Entered _update_interval_and_steps")

        interval_state = self.hass.states.get(self._interval_entity)
        steps_state = self.hass.states.get(self._steps_entity)

        _LOGGER.info(f"Fetched interval_state: {interval_state}, steps_state: {steps_state}")

        if interval_state and interval_state.state.isdigit():
            self._interval = int(interval_state.state)
        else:
            _LOGGER.warning(
                f"Interval entity {self._interval_entity} is missing or invalid. Using default value of 60 seconds."
            )
            self._interval = 60

        if steps_state and steps_state.state.isdigit():
            self._steps = int(steps_state.state)
        else:
            _LOGGER.warning(
                f"Steps entity {self._steps_entity} is missing or invalid. Using default value of 10 steps."
            )
            self._steps = 10

        _LOGGER.info(f"Updated interval to {self._interval} seconds and steps to {self._steps}")

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        while True:
            try:
                _LOGGER.debug(f"Collecting data for {self._entity_id}")
                self._update_interval_and_steps()

                state = self.hass.states.get(self._entity_id)
                if state:
                    try:
                        value = float(state.state)
                        self._add_value(value)

                        # Dynamically update the current step entity
                        current_step = len(self._values)
                        self.hass.states.async_set(self._current_step_entity, current_step, {})
                        _LOGGER.debug(f"Updated current step: {current_step}")
                    except ValueError:
                        _LOGGER.warning(f"Invalid state for {self._entity_id}: {state.state}")
                else:
                    _LOGGER.warning(f"Entity {self._entity_id} not found.")

            except Exception as e:
                _LOGGER.error(f"Error in _collect_data: {e}")

            _LOGGER.debug(f"Sleeping for {self._interval} seconds")
            await asyncio.sleep(self._interval)

    def _add_value(self, value):
        """Maintain a rolling buffer and calculate trend when steps are reached."""
        self._values.append(value)

        # Ensure the buffer size does not exceed the step count
        if len(self._values) > self._steps:
            self._values.pop(0)  # Remove the oldest value

        # Log the buffer state
        _LOGGER.debug(f"Buffer: {self._values} (size: {len(self._values)})")

        # Calculate trend if buffer size reaches the step count
        if len(self._values) == self._steps:
            self._state = self._calculate_trend()
            _LOGGER.debug(f"Trend calculated: {self._state}")

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        if not self._values:
            _LOGGER.warning("Trend calculation called with an empty buffer.")
            return 0.0  # Default to 0 if buffer is empty

        total = sum(self._values)
        trend = round(total / len(self._values), 2)
        _LOGGER.debug(f"Calculating trend: Total={total}, Count={len(self._values)}, Trend={trend}")
        return trend
