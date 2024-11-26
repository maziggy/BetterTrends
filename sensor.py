from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
from datetime import datetime, timedelta
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    if not user_entities:
        _LOGGER.error("No entities found in config entry for BetterTrends.")
        return

    # Initialize shared current_step if not already present
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if "current_step" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["current_step"] = 0

    _LOGGER.debug(f"User-provided entities for BetterTrends: {user_entities}")

    interval_entity = "number.trend_sensor_interval"
    steps_entity = "number.trend_sensor_steps"

    trend_sensors = [
        BetterTrendsSensor(hass, sensor_entity, interval_entity, steps_entity)
        for sensor_entity in user_entities
    ]

    if trend_sensors:
        async_add_entities(trend_sensors, update_before_add=True)
        _LOGGER.info(f"Added {len(trend_sensors)} BetterTrends sensors.")

        # Start the central task to manage current_step if not already running
        if "current_step_task" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["current_step_task"] = hass.loop.create_task(
                _manage_current_step(hass, user_entities)
            )
    else:
        _LOGGER.error("No valid trend sensors could be created.")


async def _manage_current_step(hass: HomeAssistant, user_entities):
    """Central task to manage current_step progression."""
    while True:
        # Retrieve the interval dynamically
        interval_state = hass.states.get("number.trend_sensor_interval")
        steps_state = hass.states.get("number.trend_sensor_steps")
        interval = 5  # Default fallback value
        steps = len(user_entities)  # Fallback to number of entities if steps_state is unavailable

        if interval_state and interval_state.state not in (None, "unknown"):
            try:
                interval = max(1, int(float(interval_state.state)))
            except ValueError:
                _LOGGER.warning(
                    "Invalid interval value for 'number.trend_sensor_interval'. Falling back to default."
                )

        if steps_state and steps_state.state not in (None, "unknown"):
            try:
                steps = max(1, int(float(steps_state.state)))
            except ValueError:
                _LOGGER.warning(
                    "Invalid steps value for 'number.trend_sensor_steps'. Falling back to default."
                )

        # Wait for the specified interval before updating steps
        await asyncio.sleep(interval)

        # Increment current_step
        current_shared_step = hass.data[DOMAIN].get("current_step", 1)  # Start at 1
        if current_shared_step < steps:  # If less than steps, increment
            new_step = current_shared_step + 1
        else:  # If at `steps`, wrap to 1
            new_step = 1

        hass.data[DOMAIN]["current_step"] = new_step

        # Update the current_step in the Home Assistant state machine
        hass.states.async_set(
            "number.trend_sensor_current_step",
            new_step,
            {
                "friendly_name": "Trend Sensor Current Step",
                "min": 1,  # Starts at 1
                "max": steps,  # Ends at `steps`
                "step": 1,
                "mode": "box",
            },
        )

        # Log the increment and interval used
        _LOGGER.debug(
            "Central task incremented current_step to %d with interval: %d seconds.",
            new_step,
            interval,
        )

class BetterTrendsSensor(SensorEntity):
    """Representation of a BetterTrends sensor."""

    def __init__(self, hass, sensor_entity, interval_entity, steps_entity):
        """Initialize the BetterTrends sensor."""
        self.hass = hass
        self._sensor_entity = sensor_entity
        self._interval_entity = interval_entity
        self._steps_entity = steps_entity
        self._state = None
        self._buffer = []
        self._lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._interval = 10  # Default interval
        self._steps = 10  # Default steps
        self._step_counter = 0
        self._data_task = None
        self._unsub_listeners = []
        self._last_invalid_log = datetime.min  # Track last invalid log time

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Better Trends {self._sensor_entity}"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"better_trends_{self._sensor_entity.replace('.', '_')}"

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    async def async_added_to_hass(self):
        """Run when entity is added to Home Assistant."""
        _LOGGER.debug("BetterTrends sensor added: %s", self._sensor_entity)

        # Ensure existing task is canceled and awaited before starting a new one
        if self._data_task:
            _LOGGER.debug("Cancelling existing _collect_data task before starting a new one.")
            self._stop_event.set()
            self._data_task.cancel()
            try:
                await self._data_task
            except asyncio.CancelledError:
                _LOGGER.debug("_collect_data task canceled successfully.")

        # Create a new stop event and start a fresh data collection task
        self._stop_event = asyncio.Event()
        self._data_task = self.hass.loop.create_task(self._collect_data())
        _LOGGER.debug("Started _collect_data task for sensor: %s", self._sensor_entity)

    async def async_will_remove_from_hass(self):
        """Handle removal of the sensor entity."""
        _LOGGER.debug("Removing BetterTrends sensor: %s", self._sensor_entity)

        # Cancel the _collect_data task and set the stop event
        if hasattr(self, "_data_task") and self._data_task:
            _LOGGER.debug("Cancelling _collect_data task during removal.")
            self._stop_event.set()  # Signal the loop to stop
            self._data_task.cancel()

        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        # Reset the shared current_step if this is the last sensor being removed
        if len(self.hass.data.get(DOMAIN, {})) == 1:  # Only 'current_step' left
            self.hass.data[DOMAIN]["current_step"] = 0
            _LOGGER.debug("Reset shared current_step to 0.")

    async def _collect_data(self):
        """Collect data for the trend sensor and ensure consistent interval usage."""
        _LOGGER.debug("Starting _collect_data task for sensor: %s", self._sensor_entity)

        reset_buffer = False

        while not self._stop_event.is_set():
            async with self._lock:
                try:
                    state = self.hass.states.get(self._sensor_entity)
                    now = datetime.utcnow()

                    # Check for invalid or unknown states
                    if not state or state.state in (None, "unknown"):
                        if now - self._last_invalid_log > timedelta(minutes=1):  # Rate-limit logging
                            _LOGGER.debug(
                                "Skipping data collection for '%s': Invalid or unknown state.",
                                self._sensor_entity,
                            )
                            self._last_invalid_log = now  # Update the last log time
                        await asyncio.sleep(self._interval)
                        continue

                    value = float(state.state)
                    if not reset_buffer:
                        self._buffer.append(value)

                    # Enforce buffer size
                    if len(self._buffer) > self._steps:
                        self._buffer.pop(0)

                    # Process buffer when full
                    if len(self._buffer) == self._steps:
                        self._state = round(sum(self._buffer) / len(self._buffer), 2)
                        _LOGGER.info(
                            "Buffer full for '%s'. Average: %s, Data: %s",
                            self._sensor_entity,
                            self._state,
                            self._buffer,
                        )
                        self.async_write_ha_state()
                        reset_buffer = True

                except ValueError:
                    _LOGGER.warning(
                        "Unable to parse state as float for '%s': %s",
                        self._sensor_entity,
                        state.state,
                    )
                except Exception as ex:
                    _LOGGER.error(
                        "Unexpected error during data collection for '%s': %s",
                        self._sensor_entity,
                        ex,
                    )

            # Clear buffer for the next cycle
            if reset_buffer:
                self._buffer.clear()
                reset_buffer = False

            await asyncio.sleep(self._interval)

    async def _manage_current_step(hass, user_entities):
        """Central task to manage current_step progression."""
        interval = 5  # Default interval for synchronization
        while True:
            # Wait for all sensors to process their data for the current step
            await asyncio.sleep(interval)

            # Increment current_step and broadcast changes
            current_shared_step = hass.data[DOMAIN].get("current_step", 0)
            new_step = (current_shared_step + 1) % len(user_entities)  # Cycle steps
            hass.data[DOMAIN]["current_step"] = new_step

            # Publish the updated step to Home Assistant state machine
            hass.states.async_set(
                "number.trend_sensor_current_step",
                new_step,
                {
                    "friendly_name": "Trend Sensor Current Step",
                    "min": 0,
                    "max": len(user_entities) - 1,
                    "step": 1,
                    "mode": "box",
                },
            )
            _LOGGER.debug("Central task incremented current_step to %d.", new_step)

    def _update_current_step(self):
        """Deprecated: Centralized current_step management is handled by _manage_current_step."""
        pass

    async def _handle_interval_change(self, event=None):
        """Handle changes to the interval entity."""
        _LOGGER.debug("Handling interval change for '%s'.", self._sensor_entity)
        self._update_interval_and_steps()

        # Cancel the existing _collect_data task
        if hasattr(self, "_data_task") and self._data_task:
            _LOGGER.debug("Cancelling existing _collect_data task due to interval change.")
            self._stop_event.set()  # Signal the current loop to stop
            self._data_task.cancel()

            # Wait for the task to cancel gracefully
            try:
                await self._data_task
            except asyncio.CancelledError:
                _LOGGER.debug("_collect_data task was cancelled successfully.")

        # Reset stop event and start a new _collect_data task
        self._stop_event = asyncio.Event()
        self._data_task = self.hass.loop.create_task(self._collect_data())
        _LOGGER.debug("Restarted _collect_data task for '%s' after interval change.", self._sensor_entity)

    async def _handle_steps_change(self, event):
        """Handle changes to the steps entity."""
        _LOGGER.debug("Handling steps change for '%s'.", self._sensor_entity)

        # Update the interval and steps dynamically
        self._update_interval_and_steps()

        # Process the buffer immediately if not empty
        async with self._lock:
            if len(self._buffer) > 0:
                self._state = round(sum(self._buffer) / len(self._buffer), 2)
                _LOGGER.info(
                    "Processing buffer due to steps change for '%s'. Processed average: %s, Data: %s",
                    self._sensor_entity,
                    self._state,
                    self._buffer,
                )
                self.async_write_ha_state()
                self._buffer.clear()  # Clear the buffer for the new cycle

        # Reset the step counter to start a fresh cycle
        self._step_counter = 0
        self._update_current_step()

        # Restart the data collection loop
        if hasattr(self, "_data_task") and self._data_task:
            _LOGGER.debug("Cancelling existing _collect_data task due to steps change.")
            self._stop_event.set()
            self._data_task.cancel()
            try:
                await self._data_task
            except asyncio.CancelledError:
                _LOGGER.debug("_collect_data task cancelled successfully.")

        self._stop_event = asyncio.Event()
        self._data_task = self.hass.loop.create_task(self._collect_data())
        _LOGGER.debug("Restarted _collect_data task for '%s' after steps change.", self._sensor_entity)

    async def _handle_sensor_state_change(self, event):
        """Handle changes to the main sensor entity."""
        _LOGGER.debug("Ignoring _handle_sensor_state_change to avoid disrupting the interval.")
        pass

    def _update_interval_and_steps(self):
        """Update interval and steps based on number entities."""
        interval_state = self.hass.states.get(self._interval_entity)
        steps_state = self.hass.states.get(self._steps_entity)

        if interval_state and steps_state:
            try:
                # Update interval and steps dynamically
                self._interval = max(1, int(float(interval_state.state)))
                self._steps = max(1, int(float(steps_state.state)))
                _LOGGER.info(
                    "Updated interval to %d seconds and steps to %d for '%s'.",
                    self._interval,
                    self._steps,
                    self._sensor_entity,
                )
            except ValueError as ex:
                _LOGGER.error(
                    "Invalid states for interval or steps (%s, %s): %s",
                    interval_state.state,
                    steps_state.state,
                    ex,
                )
        else:
            _LOGGER.warning(
                "Interval or steps entity states are unavailable for '%s'.",
                self._sensor_entity,
            )