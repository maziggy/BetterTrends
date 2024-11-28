import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
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

        # Buffers to store trend data
        self._buffers = {}

    async def async_added_to_hass(self):
        """Start trend processing when added to Home Assistant."""
        _LOGGER.debug("Starting BetterTrends Manager task.")
        await self._load_settings()
        self._initialize_buffers()
        self._start_task()

    async def async_will_remove_from_hass(self):
        """Stop trend processing when removed."""
        _LOGGER.debug("Stopping BetterTrends Manager task.")
        self._stop_task()

    def _initialize_buffers(self):
        """Initialize buffers for all configured entities."""
        for entity in self._entities:
            if entity not in self._buffers:
                self._buffers[entity] = [0.0] * self._trend_values

    def _start_task(self):
        """Start the main processing loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._main_loop())

    def _stop_task(self):
        """Stop the main processing loop."""
        if self._task:
            self._running = False
            self._task.cancel()

    async def _load_settings(self):
        """Load settings for interval and trend values."""
        self._interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=DEFAULT_INTERVAL, cast_type=int)
        self._trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=DEFAULT_INTERVAL, cast_type=int)
        self._initialize_buffers()  # Reinitialize buffers with updated settings

    async def _main_loop(self):
        """Main loop for processing trends."""
        while self._running:
            try:
                _LOGGER.debug("Processing trends for all entities.")
                await self._process_trends()
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                _LOGGER.debug("Main loop cancelled.")
                break
            except Exception as e:
                _LOGGER.error("Error in trend processing loop: %s", e)

    async def _process_trends(self):
        """Process trend calculations for each entity."""
        # Ensure buffers are initialized for all entities
        self._initialize_buffers()

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

            buffer = self._buffers[entity_id]
            buffer[self._counter] = current_value
            if self._counter == self._trend_values - 1:
                new_value = self._calculate_trend(buffer, current_value)
                self.hass.states.async_set(f"{entity_id}_last", new_value)
                _LOGGER.info("Updated trend for %s: %s", entity_id, new_value)

        # Update the trend counter
        self._counter = (self._counter + 1) % self._trend_values
        self.hass.states.async_set(TREND_COUNTER_ENTITY, self._counter)

    def _calculate_trend(self, buffer, current_value):
        """Calculate the trend-adjusted value."""
        avg = sum(buffer) / len(buffer)
        return round(current_value - avg, 2)

    def _get_ha_state(self, entity_id, default=None, cast_type=str):
        """Retrieve the state of a Home Assistant entity."""
        state = self.hass.states.get(entity_id)
        if state and state.state not in (None, "unknown"):
            try:
                return cast_type(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid state for %s: %s", entity_id, state.state)
        return default

    def add_entity(self, entity_id: str):
        """Dynamically add an entity to the manager."""
        if entity_id not in self._entities:
            self._entities.add(entity_id)
            self._buffers[entity_id] = [0.0] * self._trend_values
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
                self._state = float(entity_last.state)  # Convert to float
            except ValueError:
                _LOGGER.error(
                    "Invalid state for %s: %s is not a numeric value.",
                    f"{self._entity_id}_last",
                    entity_last.state,
                )
                self._state = None  # Reset state to None if invalid
        else:
            _LOGGER.warning(
                "Entity %s_last is unavailable or has no valid state.",
                self._entity_id,
            )
            self._state = None  # Reset state to None if unavailable