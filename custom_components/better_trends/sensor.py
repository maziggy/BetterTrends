import asyncio
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
from homeassistant.helpers.entity_registry import async_get

_LOGGER = logging.getLogger(__name__)

TREND_INTERVAL_ENTITY = "number.trend_sensor_interval"
TREND_VALUES_ENTITY = "number.trend_sensor_steps"
TREND_COUNTER_ENTITY = "number.trend_sensor_current_step"


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Store the entry_id for unique ID generation
    hass.data[DOMAIN]["entry_id"] = entry.entry_id

    entities = entry.data.get("entities", [])
    if not entities:
        _LOGGER.error("No entities configured for BetterTrends. Exiting setup.")
        return

    # Avoid duplicate registration of entities
    registry = async_get(hass)
    existing_entities = {entity.unique_id for entity in registry.entities.values()}

    # Create the manager and dynamic sensors
    manager = BetterTrendsManager(hass, entities, async_add_entities)
    async_add_entities([manager])

    # Add individual trend sensors for each configured entity
    sensors = [
        BetterTrendsSensor(manager, entity_id)
        for entity_id in entities
        if f"{DOMAIN}_{entry.entry_id}_{entity_id.replace('.', '_')}" not in existing_entities
    ]
    async_add_entities(sensors)


class BetterTrendsManager(SensorEntity):
    """Manages trend calculations for all configured sensors."""

    def __init__(self, hass: HomeAssistant, entities: list, async_add_entities):
        """Initialize the BetterTrends Manager."""
        self.hass = hass
        self._entities = set(entities)  # Use a set for dynamic updates
        self._async_add_entities = async_add_entities  # Save reference to the platform's async_add_entities
        self._interval = DEFAULT_INTERVAL
        self._trend_values = DEFAULT_TREND_VALUES
        self._counter = 0
        self._running = False
        self._task = None
        self._state = "idle"

        # Buffers to store trend data
        self._buffers = {}
        self._sensors = {}  # Track the BetterTrendsSensor instances

    async def async_added_to_hass(self):
        """Start trend processing when added to Home Assistant."""
        _LOGGER.debug("Starting BetterTrends Manager task.")
        await self._load_settings()
        self._initialize_buffers()
        await self._initialize_sensors()  # Corrected to await the coroutine
        self._start_task()

    async def async_will_remove_from_hass(self):
        """Clean up state buffers and stop trend processing."""
        for entity_id in self._sensors.keys():
            sensor_entity_id = f"sensor.better_trends_{entity_id.split('.')[-1]}"
            self.hass.states.async_remove(sensor_entity_id)
        self._stop_task()

    def _initialize_buffers(self):
        """Initialize buffers for all configured entities."""
        for entity in self._entities:
            self._buffers[entity] = []  # Initialize as an empty list
            _LOGGER.debug("Initialized buffer for %s: %s", entity, self._buffers[entity])

        self._counter = 0
        self._interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=DEFAULT_INTERVAL, cast_type=int)
        self._trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=DEFAULT_TREND_VALUES, cast_type=int)

    async def _initialize_sensors(self):
        """Initialize or reinitialize all BetterTrendsSensor instances."""
        valid_sensors = []

        for entity_id in self._entities:
            # Check if the sensor is already tracked in the manager
            if entity_id in self._sensors:
                _LOGGER.info("Sensor for %s is already initialized. Skipping creation.", entity_id)
                continue

            # Generate the unique ID for this sensor
            unique_id = f"{DOMAIN}_{self.hass.data[DOMAIN]['entry_id']}_{entity_id.replace('.', '_')}"

            # Use the entity registry to check for existing unique IDs
            registry = async_get(self.hass)
            if unique_id in {entity.unique_id for entity in registry.entities.values()}:
                _LOGGER.info("Sensor for %s already exists in the registry. Skipping creation.", entity_id)
                continue

            # Ensure the entity state is valid
            state = self.hass.states.get(entity_id)
            if not state or state.state in (None, "unknown"):
                _LOGGER.warning("Skipping entity %s: State unavailable or unknown.", entity_id)
                continue

            # Create a new sensor instance
            sensor = BetterTrendsSensor(self, entity_id)
            self._sensors[entity_id] = sensor
            valid_sensors.append(sensor)

        if valid_sensors:
            self._async_add_entities(valid_sensors)
            _LOGGER.info("Added %d new BetterTrends sensors.", len(valid_sensors))

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
        self._trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=DEFAULT_TREND_VALUES, cast_type=int)
        self._initialize_buffers()  # Reinitialize buffers with updated settings

    async def _reload_settings(self):
        """Reload settings dynamically."""
        new_interval = self._get_ha_state(TREND_INTERVAL_ENTITY, default=DEFAULT_INTERVAL, cast_type=int)
        new_trend_values = self._get_ha_state(TREND_VALUES_ENTITY, default=DEFAULT_TREND_VALUES, cast_type=int)

        if new_interval != self._interval or new_trend_values != self._trend_values:
            _LOGGER.info(
                "Settings changed. Interval: %s -> %s, Trend values: %s -> %s.",
                self._interval, new_interval, self._trend_values, new_trend_values,
            )
            self._interval = new_interval
            self._trend_values = new_trend_values

            # Update existing sensors
            for sensor in self._sensors.values():
                sensor.update_settings(new_interval, new_trend_values)

            # Reinitialize buffers to match new trend values
            self._initialize_buffers()

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

    async def _process_trends(self):
        """Process trend calculations for each entity."""
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

            # Get the buffer for the entity
            buffer = self._buffers.setdefault(entity_id, [])
            buffer.append(current_value)

            _LOGGER.debug(f"buffer for entity {entity_id}: {buffer}")

            # If the buffer is full, calculate the trend and reset the buffer
            if len(buffer) >= self._trend_values:
                trend_value = self._calculate_trend(buffer)  # Updated to only pass the buffer

                sensor_entity_id = f"sensor.better_trends_{entity_id.split('.')[-1]}"
                self.hass.states.async_set(sensor_entity_id, trend_value)
                _LOGGER.info("Updated trend for %s: %s", sensor_entity_id, trend_value)
                self._buffers[entity_id] = []  # Reset the buffer

        # After updating entities, increment the trend counter
        self._counter = (self._counter + 1) % (self._trend_values + 1)  # Cycle from 0 to `steps`
        self.hass.states.async_set(TREND_COUNTER_ENTITY, self._counter)

        # Log the global current step
        _LOGGER.debug("Global current step updated to %d.", self._counter)

    def _calculate_trend(self, buffer: list[float]) -> float:
        """Calculate the trend-adjusted value."""
        if not buffer:
            return 0.0  # Default to 0.0 if the buffer is empty

        avg = sum(buffer) / len(buffer)
        trend_value = round(buffer[-1] - avg, 2)

        # Normalize -0.0 to 0.0
        if trend_value == -0.0:
            trend_value = 0.0

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

class BetterTrendsSensor(SensorEntity):
    """Represents an individual trend sensor."""

    def __init__(self, manager: BetterTrendsManager, entity_id: str):
        """Initialize a BetterTrends sensor."""
        self._manager = manager
        self._entity_id = entity_id
        self._state = None
        self._interval = manager._interval
        self._trend_values = manager._trend_values

    async def async_added_to_hass(self):
        """Initialize the sensor after being added to Home Assistant."""
        _LOGGER.debug("Initializing BetterTrends sensor for %s.", self._entity_id)
        self.update_settings(self._manager._interval, self._manager._trend_values)

    def update_settings(self, interval: int, trend_values: int):
        """Update sensor settings dynamically."""
        _LOGGER.info(
            "Updating sensor %s settings: Interval: %s -> %s, Trend values: %s -> %s.",
            self._entity_id, self._interval, interval, self._trend_values, trend_values,
        )
        self._interval = interval
        self._trend_values = trend_values

    @property
    def unique_id(self):
        """Return a unique ID for the sensor."""
        entry_id = self._manager.hass.data.get(DOMAIN, {}).get("entry_id", "default")
        return f"{DOMAIN}_{entry_id}_{self._entity_id.replace('.', '_')}"

    @property
    def name(self):
        """Return the name of the sensor."""
        # Avoid repetitive naming
        return f"BetterTrends {self._entity_id.split('.')[-1]}"

    @property
    def state(self):
        """Return the current state of the sensor."""
        return self._state