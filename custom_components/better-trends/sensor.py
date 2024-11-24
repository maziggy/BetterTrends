from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import logging
import asyncio
import time

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    if not user_entities:
        _LOGGER.error("No entities found in config entry for BetterTrends.")
        return

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
    else:
        _LOGGER.error("No valid trend sensors could be created.")


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
        self._steps = 10     # Default steps
        self._current_step = 0
        self._data_task = None
        self._unsub_listeners = []

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

        # Cancel any existing task
        if hasattr(self, "_data_task") and self._data_task:
            _LOGGER.debug("Cancelling existing _collect_data task before starting a new one.")
            self._data_task.cancel()

        # Create a stop event for the task
        self._stop_event = asyncio.Event()

        # Start a new task for data collection
        self._data_task = self.hass.loop.create_task(self._collect_data())

        # Set up listeners
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, self._interval_entity, self._handle_interval_change
            )
        )
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, self._steps_entity, self._handle_steps_change
            )
        )
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, self._sensor_entity, self._handle_sensor_state_change
            )
        )
        
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

    async def _collect_data(self):
        """Collect data for the trend sensor and ensure consistent interval usage."""
        _LOGGER.debug("Starting _collect_data loop for sensor: %s", self._sensor_entity)

        while not self._stop_event.is_set():  # Loop until stop event is triggered
            async with self._lock:
                try:
                    # Retrieve the latest state from the associated sensor
                    state = self.hass.states.get(self._sensor_entity)
                    if state and state.state not in (None, "unknown"):
                        try:
                            value = float(state.state)
                            self._buffer.append(value)

                            # Strictly enforce buffer size limit
                            while len(self._buffer) > self._steps:
                                self._buffer.pop(0)

                            # Update current_step
                            new_step = len(self._buffer)
                            if new_step != self._current_step:
                                self._current_step = new_step
                                current_step_entity_id = "number.trend_sensor_current_step"
                                self.hass.states.async_set(
                                    current_step_entity_id,
                                    self._current_step,
                                    {
                                        "friendly_name": "Trend Sensor Current Step",
                                        "min": 0,
                                        "max": self._steps,
                                        "step": 1,
                                        "mode": "box",
                                    },
                                )
                                _LOGGER.debug(
                                    "Updated current_step to %d (buffer size: %d)",
                                    self._current_step,
                                    len(self._buffer),
                                )

                            # Process buffer if full
                            if self._current_step == self._steps:
                                _LOGGER.info("Buffer full, processing data and resetting steps.")
                                self._state = round(sum(self._buffer) / len(self._buffer), 2)
                                self._buffer.clear()
                                self._current_step = 0

                                # Update the sensor state
                                self.async_write_ha_state()

                        except ValueError:
                            _LOGGER.warning(
                                "Unable to parse state as float: %s",
                                state.state,
                            )
                    else:
                        _LOGGER.warning(
                            "No valid state for entity %s. Skipping this cycle.",
                            self._sensor_entity,
                        )

                except Exception as ex:
                    _LOGGER.error("Unexpected error during data collection: %s", ex)

            # Fetch the latest interval dynamically
            self._update_interval_and_steps()

            # Sleep for the interval or exit early if the stop event is triggered
            sleep_interval = max(self._interval, 1)  # Enforce a minimum sleep of 1 second
            _LOGGER.debug(
                "Sleeping for %d seconds (interval: %d, steps: %d).",
                sleep_interval,
                self._interval,
                self._steps,
            )
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_interval)
            except asyncio.TimeoutError:
                pass
                                
    async def _handle_interval_change(self, event=None):
        """Handle changes to the interval entity."""
        _LOGGER.debug("sensor.py -> _handle_interval_change")
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

    async def _handle_steps_change(self, event):
        """Handle changes to the steps entity."""
        _LOGGER.debug(f"sensor.py -> _handle_steps_change")
        self._update_interval_and_steps()

    async def _handle_sensor_state_change(self, event):
        """Handle changes to the main sensor entity."""
        _LOGGER.debug("Ignoring _handle_sensor_state_change to avoid disrupting the interval.")
        # Do not trigger immediate collection to prevent overwriting the interval-based updates.
        pass
        
    def _update_interval_and_steps(self):
        """Update interval and steps based on number entities."""
        interval_state = self.hass.states.get(self._interval_entity)
        steps_state = self.hass.states.get(self._steps_entity)

        _LOGGER.debug(f"sensor.py -> _update_interval_and_steps -> interval_state: {interval_state}, steps_state: {steps_state}")
        if interval_state and steps_state:
            try:
                # Update interval and steps dynamically
                self._interval = max(1, int(float(interval_state.state)))  # Minimum interval of 1 second
                self._steps = max(1, int(float(steps_state.state)))  # Minimum steps of 1
                _LOGGER.info(f"Updated interval to {self._interval} seconds and steps to {self._steps}")
            except ValueError:
                _LOGGER.error(f"Invalid states for interval or steps: {interval_state.state}, {steps_state.state}")
        else:
            _LOGGER.warning("Interval or steps entity states are unavailable.")
