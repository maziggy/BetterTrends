import asyncio
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES, TREND_INTERVAL_ENTITY, TREND_VALUES_ENTITY, \
    TREND_COUNTER_ENTITY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    if DOMAIN in hass.data:
        manager = hass.data[DOMAIN]
        _LOGGER.debug("Adding new entities to existing BetterTrends Manager.")
        new_entities = [e for e in entry.data.get("entities", []) if e not in manager._entities]
        if new_entities:
            manager.add_entities(new_entities)
            better_trends_sensors = [BetterTrendsSensor(manager, entity_id) for entity_id in new_entities]
            async_add_entities(better_trends_sensors)
        return

    _LOGGER.debug("Starting BetterTrends setup with entry data: %s", entry.data)
    entities = entry.data.get("entities", [])
    if not entities:
        _LOGGER.error("No entities configured for BetterTrends. Exiting setup.")
        return

    # Initialize the manager
    manager = BetterTrendsManager(hass, entities)
    hass.data[DOMAIN] = manager  # Store the manager instance globally
    async_add_entities([manager])

    # Add user-defined entities
    better_trends_sensors = [BetterTrendsSensor(manager, entity_id) for entity_id in entities]
    async_add_entities(better_trends_sensors)
    _LOGGER.debug("Added BetterTrends user entities: %s", entities)


class BetterTrendsManager(SensorEntity):
    def __init__(self, hass: HomeAssistant, entities: list):
        """Initialize the BetterTrends manager."""
        self.hass = hass
        self._entities = set(entities)
        self._interval = DEFAULT_INTERVAL
        self._trend_values = DEFAULT_TREND_VALUES
        self._trend_counter = 0
        self._state = "idle"
        self._buffers = {}
        self._counter_entity_id = TREND_COUNTER_ENTITY
        self._running = False  # Initialize the _running flag
        self._task = None  # Initialize the _task attribute

    async def async_added_to_hass(self):
        """Handle the addition of the BetterTrends Manager entity."""
        _LOGGER.debug("BetterTrends Manager async_added_to_hass started.")
        await asyncio.sleep(1)
        await self._reload_settings()

        # Ensure the counter entity exists
        for attempt in range(5):
            registry = er.async_get(self.hass)
            existing_counter = registry.async_get(TREND_COUNTER_ENTITY)

            if existing_counter:
                _LOGGER.debug("Counter entity found: %s", existing_counter.entity_id)
                self._counter_entity_id = existing_counter.entity_id
                self._trend_counter = int(self.hass.states.get(self._counter_entity_id).state or 0)
                break
            else:
                if attempt < 4:
                    _LOGGER.warning("Counter entity not found. Retrying (%d/5)...", attempt + 1)
                    await asyncio.sleep(1)
                else:
                    _LOGGER.error(
                        "Expected counter entity 'TREND_COUNTER_ENTITY' not found in registry. "
                        "Please check your configuration."
                    )
                    return

        # Reflect the counter state and start the main loop
        self._state = self._trend_counter
        self.async_write_ha_state()
        _LOGGER.debug("Trend counter reflected in state: %d", self._state)
        self._start_task()  # Start the main loop

    async def _initialize_buffers(self):
        """Initialize trend calculation buffers for all entities."""
        for entity in self._entities:
            self._buffers[entity] = []
        self._trend_counter = 0
        self.hass.states.async_set(self._counter_entity_id, self._trend_counter)
        _LOGGER.debug("Trend counter reset to 0 and initialized.")

    async def async_will_remove_from_hass(self):
        """Handle cleanup when the manager is removed."""
        _LOGGER.debug("Stopping BetterTrends Manager task.")
        await self._stop_task()

    async def _stop_task(self):
        """Stop the background task, if running."""
        if self._task:
            self._task.cancel()
            self._running = False
            try:
                await self._task  # Wait for task to handle the cancellation
            except asyncio.CancelledError:
                pass  # Ignore the cancellation exception

    async def _restart_task(self):
        """Restart the background task."""
        _LOGGER.debug("Restarting main_loop")

        # Ensure buffers are reset
        await self._initialize_buffers()

        # Stop the current task
        if self._task:
            self._task.cancel()
            try:
                await self._task  # Properly await the cancellation
            except asyncio.CancelledError:
                _LOGGER.debug("Previous task cancelled successfully.")
            self._task = None  # Clear the reference to the old task

        # Start the new task
        self._start_task()

    def _start_task(self):
        """Start the main processing loop."""
        if not self._running:
            self._running = True
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._main_loop())
            else:
                _LOGGER.warning("Attempted to start a new task, but an existing task is still running.")

    async def _main_loop(self):
        while self._running:
            try:
                # Reload settings dynamically before processing trends
                await self._reload_settings()

                _LOGGER.debug("Processing trends for all entities.")
                await self._process_trends()  # Await the trend processing
                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                _LOGGER.debug("Main loop cancelled.")
                break
            except Exception as e:
                _LOGGER.error("Error in trend processing loop: %s", e)

    async def _process_trends(self):
        """Process trend calculations for all configured entities."""
        for entity_id in self._entities:
            _LOGGER.debug("Processing trends for entity_id: %s (expected monitored entity)", entity_id)

            state = self.hass.states.get(entity_id)
            if not state or state.state in (None, "unknown"):
                _LOGGER.warning("Skipping entity %s: State unavailable or unknown.", entity_id)
                continue

            try:
                current_value = float(state.state)
            except ValueError:
                _LOGGER.error("Skipping entity %s: State is not numeric.", entity_id)
                continue

            buffer = self._buffers.setdefault(entity_id, [])
            buffer.append(current_value)

            _LOGGER.debug("Buffer for entity %s: %s", entity_id, buffer)

            if self._trend_counter >= self._trend_values:
                # Ensure _calculate_trend is called correctly with entity_id
                trend_value = self._calculate_trend(entity_id, buffer)
                sensor_entity_id = f"sensor.bettertrends_{entity_id.replace('.', '_')}"

                if trend_value is not None:
                    self.hass.states.async_set(sensor_entity_id, trend_value)
                    _LOGGER.info("Updated trend for %s: %s", sensor_entity_id, trend_value)

                # Clear the buffer after processing
                self._buffers[entity_id] = []
            else:
                _LOGGER.debug("Buffer for %s is not yet full. Skipping trend update.", entity_id)

        # Increment trend counter
        previous_counter = self._trend_counter
        self._trend_counter = (self._trend_counter + 1) % (self._trend_values + 1)

        if self._trend_counter != previous_counter:
            self.hass.states.async_set(TREND_COUNTER_ENTITY, self._trend_counter)
            _LOGGER.debug("Trend counter updated from %d to %d", previous_counter, self._trend_counter)
        else:
            _LOGGER.debug("Trend counter remains unchanged at %d", self._trend_counter)

    async def _reload_settings(self):
        """Reload settings for interval, steps, and counter."""
        interval_entity = self.hass.states.get(TREND_INTERVAL_ENTITY)
        steps_entity = self.hass.states.get(TREND_VALUES_ENTITY)

        new_interval = int(interval_entity.state) if interval_entity else DEFAULT_INTERVAL
        new_trend_values = int(steps_entity.state) if steps_entity else DEFAULT_TREND_VALUES

        if self._interval != new_interval or self._trend_values != new_trend_values:
            self._interval = new_interval
            self._trend_values = new_trend_values
            await self._restart_task()

        _LOGGER.debug(
            "Settings reloaded: interval=%d, trend_values=%d, counter=%d",
            self._interval,
            self._trend_values,
            self._trend_counter,
        )

    def _calculate_trend(self, entity_id, buffer: list[float]) -> float:
        """Calculate the trend-adjusted value."""
        if not buffer:
            state = self.hass.states.get(f"sensor.bettertrends_{entity_id.replace('.', '_')}")
            if state:
                return float(state.state)
            return None

        avg = sum(buffer) / len(buffer)
        last = float(self.hass.states.get(entity_id).state)  # Match monitored entity format
        trend_value = round(last - avg, 2)

        if trend_value == -0.0:
            trend_value = 0.0

        _LOGGER.debug("Trend value for %s: %s", entity_id, trend_value)
        return trend_value

    def _get_ha_state(self, entity_id, default=None, cast_type=str):
        """Retrieve the state of a Home Assistant entity."""
        state = self.hass.states.get(entity_id)
        if state and state.state not in (None, "unknown"):
            try:
                return cast_type(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid state for %s: %s", entity_id, state.state)
        return default

    def add_entities(self, new_entities: list):
        """Dynamically add new entities to the manager."""
        for entity_id in new_entities:
            if entity_id not in self._entities:
                self._entities.add(entity_id)
                if entity_id not in self._buffers:
                    self._buffers[entity_id] = []
                _LOGGER.info("Added entity %s to BetterTrends.", entity_id)

    def remove_entity(self, entity_id: str):
        """Dynamically remove an entity from the manager."""
        if entity_id in self._entities:
            self._entities.remove(entity_id)
            if entity_id in self._buffers:
                del self._buffers[entity_id]
            _LOGGER.info("Removed entity %s from BetterTrends.", entity_id)

    @property
    def name(self):
        """Return the name of the manager."""
        return "BetterTrends Manager"

    @property
    def state(self):
        """Return the state of the manager."""
        return self._state

    @property
    def should_poll(self):
        """Disable polling."""
        return False


class BetterTrendsSensor(SensorEntity):
    """Represents an individual trend sensor."""

    def __init__(self, manager: BetterTrendsManager, entity_id: str):
        """Initialize a BetterTrends sensor."""
        self._manager = manager
        self._entity_id = entity_id
        self._unique_id = f"sensor.bettertrends_{entity_id.replace('.', '_')}"
        _LOGGER.debug("Initializing BetterTrends sensor: %s with unique_id: %s", self._entity_id, self._unique_id)

    async def async_added_to_hass(self):
        """Handle entity addition."""
        _LOGGER.debug("BetterTrends sensor added for %s.", self._entity_id)

        # Check if the state already exists in HA
        existing_state = self.hass.states.get(self.unique_id)
        if existing_state and existing_state.state != "unavailable":
            _LOGGER.debug(
                "State for %s already exists: %s. Reusing state.", self.unique_id, existing_state.state
            )
            self.hass.states.async_set(self.unique_id, existing_state.state)
        else:
            _LOGGER.debug("No valid existing state for %s. Initializing state to 0.0.", self.unique_id)
            self.hass.states.async_set(self.unique_id, 0.0)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"BetterTrends {self._entity_id}"

    @property
    def unique_id(self):
        """Return the cached unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the current state of the sensor."""
        state = self.hass.states.get(self.unique_id)
        if state:
            _LOGGER.debug("Fetched state for %s: %s", self.unique_id, state.state)
            return state.state
        _LOGGER.debug("State for %s is None. Returning None.", self.unique_id)
        return None

    async def async_update(self):
        """No-op update method. State is updated by the manager."""
        _LOGGER.debug("async_update called for %s but skipped.", self._entity_id)
