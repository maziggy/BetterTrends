import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging

_LOGGER = logging.getLogger(__name__)

TREND_INTERVAL_ENTITY = "number.trend_sensor_interval"
TREND_VALUES_ENTITY = "number.trend_sensor_steps"
TREND_COUNTER_ENTITY = "number.trend_sensor_current_step"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    entities = entry.data.get("entities", [])

    if not entities:
        _LOGGER.error("No entities configured for BetterTrends. Exiting setup.")
        return

    # Create the manager and dynamic sensors
    manager = BetterTrendsManager(hass, entities)
    async_add_entities([manager])

    # Add individual trend sensors for each configured entity
    sensors = [
        BetterTrendsSensor(manager, entity_id) for entity_id in entities
    ]
    async_add_entities(sensors)


class BetterTrendsManager(SensorEntity):
    """Manages trend calculations for all configured sensors."""

    def __init__(self, hass: HomeAssistant, entities: list):
        """Initialize the BetterTrends Manager."""
        self.hass = hass
        self._entities = set(entities)  # Use a set for dynamic updates
        self._interval = DEFAULT_INTERVAL
        self._trend_values = DEFAULT_TREND_VALUES
        self._counter = 0
        self._running = False
        self._task = None
        self._state = "idle"

        # Buffers start empty and dynamically grow
        self._buffers = {}

    async def async_added_to_hass(self):
        """Start trend processing when added to Home Assistant."""
        _LOGGER.debug("Starting BetterTrends Manager task.")
        await self._load_settings()
        self._initialize_buffers()
        self._initialize_states()
        self._start_task()

    async def async_will_remove_from_hass(self):
        """Stop trend processing when removed."""
        _LOGGER.debug("Stopping BetterTrends Manager task.")
        self._stop_task()

    def _initialize_buffers(self):
        """Initialize buffers for all configured entities if they don't exist."""
        for entity in self._entities:
            if entity not in self._buffers:
                self._buffers[entity] = []  # Initialize as an empty list
                _LOGGER.debug("Initialized buffer for %s: %s", entity, self._buffers[entity])

    def _initialize_states(self):
        """Set all entities' states to 0.0 initially."""
        for entity in self._entities:
            self.hass.states.async_set(f"{entity}_last", 0.0)
            _LOGGER.info("Initialized state for %s to 0.0", entity)

    def _restart_task(self):
        """Restart the main task to apply updated settings."""
        self._stop_task()
        self._start_task()

    def _stop_task(self):
        """Stop the main processing loop."""
        if self._task:
            self._running = False
            self._task.cancel()

    def _start_task(self):
        """Start the main processing loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._main_loop())

    async def _reload_settings(self):
        """Reload settings dynamically and adjust the main loop if needed."""
        new_interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=5, cast_type=int)

        if new_interval != self._interval:
            _LOGGER.info("Interval changed from %s to %s. Restarting main loop.", self._interval, new_interval)
            self._interval = new_interval

            # Restart the task to apply the new interval
            self._restart_task()

    async def _reload_trend_values(self):
        """Reload trend values dynamically and reset buffers."""
        new_trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=5, cast_type=int)

        if new_trend_values != self._trend_values:
            _LOGGER.info("Trend values changed from %s to %s. Resetting buffers.", self._trend_values, new_trend_values)
            self._trend_values = new_trend_values
            self._initialize_buffers()  # Reset buffers for all entities

    async def _load_settings(self):
        """Load settings for interval and trend values."""
        new_interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=self._interval, cast_type=int)
        new_trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=self._trend_values, cast_type=int)

        if new_interval != self._interval:
            _LOGGER.info("Interval changed from %d to %d. Restarting task.", self._interval, new_interval)
            self._interval = new_interval
            self._restart_task()

        if new_trend_values != self._trend_values:
            _LOGGER.info("Trend values changed from %d to %d. Reinitializing buffers.", self._trend_values,
                         new_trend_values)
            self._trend_values = new_trend_values
            self._buffers = {}  # Clear buffers to enforce reinitialization
            self._initialize_buffers()

    def _get_ha_state(self, entity_id: str, default=None, cast_type=str):
        """Retrieve the state of a Home Assistant entity."""
        state = self.hass.states.get(entity_id)
        if state and state.state not in (None, "unknown", "unavailable"):
            try:
                return cast_type(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid state for %s: %s", entity_id, state.state)
        else:
            _LOGGER.warning("%s is not available. Using default.", entity_id)
        return default

    def _resize_buffers(self):
        """Resize the buffers to match the new trend values."""
        for entity_id, buffer in self._buffers.items():
            if len(buffer) > self._trend_values:
                # Truncate buffer if too large
                self._buffers[entity_id] = buffer[:self._trend_values]
            else:
                # Expand buffer with zeroes if too small
                self._buffers[entity_id].extend([0.0] * (self._trend_values - len(buffer)))
            _LOGGER.debug("Resized buffer for %s: %s", entity_id, self._buffers[entity_id])

    def _restart_task(self):
        """Restart the main processing task."""
        self._stop_task()
        self._start_task()

    async def _main_loop(self):
        """Main loop for processing trends with dynamic interval adjustment."""
        while self._running:
            try:
                _LOGGER.debug("Processing trends for all entities.")
                await self._process_trends()

                # Sleep for the current interval duration
                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                _LOGGER.debug("Main loop cancelled.")
                break
            except Exception as e:
                _LOGGER.error("Error in trend processing loop: %s", e)

    async def _process_trends(self):
        """Process trend calculations for each entity."""
        # Dynamically reload settings
        await self._reload_settings()
        await self._reload_trend_values()

        for entity_id in self._entities:
            state = self.hass.states.get(entity_id)
            if not state or state.state in (None, "unknown"):
                _LOGGER.warning("Skipping entity %s: State unavailable or unknown.", entity_id)
                continue

            try:
                current_value = float(state.state)
            except ValueError:
                _LOGGER.error("Skipping entity %s: State is not numeric.", entity_id)
                continue

            # Add the current value to the buffer
            buffer = self._buffers[entity_id]
            buffer.append(current_value)

            _LOGGER.debug("Buffer for %s: %s", entity_id, buffer)

            # When the buffer reaches the configured steps
            if len(buffer) == self._trend_values:
                # Calculate the trend
                new_value = self._calculate_trend(buffer)
                self.hass.states.async_set(f"{entity_id}_last", new_value)
                _LOGGER.info("Updated trend for %s: %s", entity_id, new_value)

                # Reset the buffer for the next cycle
                self._buffers[entity_id] = []

            # Update the current step count
            self._counter = len(buffer)
            self.hass.states.async_set(TREND_COUNTER_ENTITY, self._counter)

    def _calculate_trend(self, buffer):
        """Calculate the trend-adjusted value."""
        avg = sum(buffer) / len(buffer)
        current_value = buffer[-1]  # Use the latest value
        return round(current_value - avg, 2)

    def add_entity(self, entity_id: str):
        """Dynamically add an entity to the manager."""
        if entity_id not in self._entities:
            self._entities.add(entity_id)
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
        self._state = None

    async def async_added_to_hass(self):
        """Handle entity addition."""
        _LOGGER.debug("Added BetterTrends sensor for %s.", self._entity_id)
        self.update()  # Initial update

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"BetterTrends {self._entity_id}"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"better_trends_{self._entity_id}"

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state

    def update(self):
        """Update the state from the manager."""
        entity_last = self.hass.states.get(f"{self._entity_id}_last")
        if entity_last and entity_last.state not in (None, "unknown"):
            try:
                self._state = float(entity_last.state)
            except ValueError:
                self._state = None
        else:
            self._state = None
