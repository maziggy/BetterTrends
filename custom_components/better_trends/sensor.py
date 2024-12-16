import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES, TREND_INTERVAL_ENTITY, TREND_VALUES_ENTITY, \
    TREND_COUNTER_ENTITY
import logging
import sys

_LOGGER = logging.getLogger(__name__)


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
    sensors = []
    for entity_id in entities:
        unique_id = f"sensor.bettertrends_{entity_id.replace('.', '_')}"
        if unique_id not in hass.states.async_all():
            sensors.append(BetterTrendsSensor(manager, entity_id))
        else:
            _LOGGER.warning("Entity %s already exists. Skipping creation.", unique_id)

    async_add_entities(sensors)


class BetterTrendsManager(SensorEntity):
    """Manages trend calculations for all configured sensors."""

    def __init__(self, hass: HomeAssistant, entities: list):
        """Initialize the BetterTrends Manager."""
        self.hass = hass
        self._entities = set(entities)
        self._interval = DEFAULT_INTERVAL
        self._trend_values = DEFAULT_TREND_VALUES
        self._counter = 0
        self._running = False
        self._task = None
        self._state = "idle"
        self._buffers = {}

        # Unique IDs for special entities
        self._counter_entity_id = TREND_COUNTER_ENTITY

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
            self._buffers[entity] = []
        # Reset the counter explicitly
        self._counter = 0
        self.hass.states.async_set(self._counter_entity_id, self._counter)
        _LOGGER.debug("Trend counter reset to 0 and entity created.")

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
                # Reload settings dynamically before processing trends
                await self._reload_settings()

                _LOGGER.debug("Processing trends for all entities.")
                await self._process_trends()
                await asyncio.sleep(self._interval)

            except asyncio.CancelledError:
                _LOGGER.debug("Main loop cancelled.")
                break
            except Exception as e:
                _LOGGER.error("Error in trend processing loop: %s", e)

    async def _reload_settings(self):
        """Reload settings dynamically."""
        new_interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=DEFAULT_INTERVAL, cast_type=int)
        new_trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=DEFAULT_TREND_VALUES, cast_type=int)

        buffers_reset_required = False

        # Update interval if it has changed
        if new_interval != self._interval:
            _LOGGER.info("Interval changed from %s to %s. Restarting main loop.", self._interval, new_interval)
            self._interval = new_interval
            buffers_reset_required = True

        # Update trend values if they have changed
        if new_trend_values != self._trend_values:
            _LOGGER.info("Trend values changed from %s to %s. Reinitializing buffers.", self._trend_values,
                         new_trend_values)
            self._trend_values = new_trend_values
            buffers_reset_required = True

        # Only reset buffers and counter if required
        if buffers_reset_required:
            self._initialize_buffers()
            _LOGGER.debug("Buffers reinitialized and counter reset after configuration change.")

    async def _process_trends(self):
        """Process trend calculations for all configured entities."""
        for entity_id in self._entities:
            state = self.hass.states.get(entity_id)
            if not state or state.state in (None, "unknown"):
                continue

            try:
                current_value = float(state.state)
            except ValueError:
                continue

            buffer = self._buffers.setdefault(entity_id, [])
            buffer.append(current_value)

            if self._counter >= self._trend_values:
                trend_value = self._calculate_trend(entity_id, buffer)
                sensor_entity_id = f"sensor.bettertrends_{entity_id.replace('.', '_')}"

                if trend_value is not None:
                    self.hass.states.async_set(sensor_entity_id, trend_value)

                self._counter = 0
                self._buffers[entity_id] = []

        previous_counter = self._counter
        self._counter += 1 #(self._counter + 1) % (self._trend_values + 1)

        if self._counter != previous_counter:
            self.hass.states.async_set(self._counter_entity_id, self._counter)
            _LOGGER.debug("Trend counter updated to %d", self._counter)

    def _calculate_trend(self, entity_id, buffer: list[float]) -> float:
        """Calculate the trend-adjusted value."""
        if not buffer:
            # Retrieve last known state from BetterTrends sensor
            state = self.hass.states.get(f"sensor.bettertrends_{entity_id.replace('.', '_')}")
            if state:
                return float(state.state)
            return None

        avg = sum(buffer) / len(buffer)
        last = float(self.hass.states.get(entity_id).state)  # Ensure this matches the monitored entity format
        trend_value = round(last - avg, 2)

        # Normalize -0.0 to 0.0
        if trend_value == -0.0:
            trend_value = 0.0

        _LOGGER.debug(f"Trend value for {entity_id}: {trend_value}")
        return trend_value

    def _get_ha_state(self, entity_id, default=None, cast_type=str):
        """Retrieve the state of a Home Assistant entity."""
        state = self.hass.states.get(entity_id)
        if state and state.state not in (None, "unknown"):
            try:
                return cast_type(state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid state for %s: %s", entity_id, state.state)
        else:
            _LOGGER.debug("State for %s is unavailable. Using default: %s", entity_id, default)
        return default

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

    async def async_added_to_hass(self):
        """Handle entity addition."""
        _LOGGER.debug("Added BetterTrends sensor for %s.", self._entity_id)

        # Check if the state already exists
        existing_state = self.hass.states.get(self.unique_id)
        if existing_state is None or existing_state.state in (None, "unknown"):
            _LOGGER.debug("Initializing state for %s to 0.0.", self.unique_id)
            self.hass.states.async_set(self.unique_id, 0.0)
        else:
            _LOGGER.debug("State for %s already exists: %s. Skipping initialization.", self.unique_id,
                          existing_state.state)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"BetterTrends {self._entity_id}"

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        return f"sensor.bettertrends_{self._entity_id.replace('.', '_')}"

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
        #_LOGGER.debug("async_update called for %s but skipped.", self._entity_id)
        return
