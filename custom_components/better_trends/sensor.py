import asyncio
import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.core import callback
import traceback
from asyncio import Lock

from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES, TREND_INTERVAL_ENTITY, TREND_VALUES_ENTITY, \
    TREND_COUNTER_ENTITY

_LOGGER = logging.getLogger(__name__)


@callback
def monitor_trend_counter(hass, event):
    """Monitor external changes to the trend counter state."""
    entity_id = TREND_COUNTER_ENTITY
    if event.data.get("entity_id") == entity_id:
        old_state = event.data.get("old_state").state if event.data.get("old_state") else None
        new_state = event.data.get("new_state").state if event.data.get("new_state") else None

        # Skip redundant updates where the state hasn't changed
        if old_state == new_state:
            _LOGGER.debug("No change in counter state. Current state: %s", new_state)
            return

        _LOGGER.info("Trend counter state changed externally: %s -> %s", old_state, new_state)

        # Handle unexpected transitions
        try:
            new_value = int(new_state)
            if old_state and old_state.isdigit():
                old_value = int(old_state)
                expected_next = (old_value + 1) % (DEFAULT_TREND_VALUES + 1)
                if new_value != expected_next:
                    _LOGGER.warning(
                        "Unexpected external counter transition: %d -> %d. Expected: %d.",
                        old_value, new_value, expected_next
                    )
        except ValueError:
            _LOGGER.error("Non-integer state detected for trend counter: %s", new_state)


@callback
def monitor_steps_entity(hass, event):
    """Monitor changes to the steps entity."""
    _LOGGER.debug("monitor_steps_entity called with event: %s", event)
    entity_id = TREND_VALUES_ENTITY
    if event.data.get("entity_id") == entity_id:
        new_state = event.data.get("new_state").state if event.data.get("new_state") else None
        old_state = event.data.get("old_state").state if event.data.get("old_state") else None

        if new_state == old_state:
            _LOGGER.debug("No change in TREND_VALUES_ENTITY state. Current state: %s", new_state)
            return

        _LOGGER.info("TREND_VALUES_ENTITY state changed: %s -> %s", old_state, new_state)

        if new_state and new_state.isdigit():
            trend_values = int(new_state)
            try:
                manager = hass.data[DOMAIN]
                if manager:
                    _LOGGER.debug("Restarting BetterTrendsManager for updated steps: %d", trend_values)

                    # Schedule the restart task safely on the event loop
                    def restart_manager():
                        hass.async_create_task(manager._clear_and_restart())

                    hass.loop.call_soon_threadsafe(restart_manager)
                    _LOGGER.info("BetterTrendsManager restart scheduled for updated steps: %d", trend_values)
                else:
                    _LOGGER.error("BetterTrendsManager is not initialized. Cannot restart.")
            except Exception as e:
                _LOGGER.error("Error scheduling BetterTrendsManager restart for updated steps: %s", e)
        else:
            _LOGGER.warning("Invalid TREND_VALUES_ENTITY state: %s. Skipping update.", new_state)

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
    manager = BetterTrendsManager(hass, entities, entry)
    hass.data[DOMAIN] = manager  # Store the manager instance globally
    async_add_entities([manager])

    # Check for existing entities in the registry
    registry = er.async_get(hass)
    for entity_id in entities:
        entity_entry = registry.async_get(f"sensor.bettertrends_{entity_id.replace('.', '_')}")
        if entity_entry:
            _LOGGER.debug("Entity %s already exists in registry. Reusing.", entity_id)
        else:
            _LOGGER.debug("Adding new entity: %s", entity_id)

    # Add user-defined entities
    better_trends_sensors = [BetterTrendsSensor(manager, entity_id) for entity_id in entities]
    async_add_entities(better_trends_sensors)
    _LOGGER.debug("Added BetterTrends user entities: %s", entities)

    # Listen for state changes in TREND_COUNTER_ENTITY
    hass.bus.async_listen("state_changed", lambda event: monitor_trend_counter(hass, event))
    hass.bus.async_listen("state_changed", lambda event: monitor_steps_entity(hass, event))
    hass.bus.async_listen("state_changed", lambda event: _LOGGER.debug("state_changed event: %s", event))

class BetterTrendsManager(SensorEntity):
    """Manages trend calculation and state updates."""

    def __init__(self, hass: HomeAssistant, entities: list, config_entry):
        """Initialize the BetterTrends manager."""
        self.hass = hass
        self._entities = set(entities)
        self._config_entry = config_entry
        self._interval = DEFAULT_INTERVAL
        self._trend_values = DEFAULT_TREND_VALUES
        self._trend_counter = 0
        self._state = "idle"
        self._buffers = {}
        self._counter_entity_id = TREND_COUNTER_ENTITY
        self._running = False
        self._task = None
        self._counter_lock = Lock()  # Add a lock for counter updates

    async def async_added_to_hass(self):
        """Handle the addition of the BetterTrends Manager entity."""
        _LOGGER.debug("BetterTrends Manager async_added_to_hass called.")

        # Allow Home Assistant to stabilize entity states
        await asyncio.sleep(2)

        # Ensure `TREND_INTERVAL_ENTITY` and `TREND_VALUES_ENTITY` are initialized
        self._initialize_entities()

        # Ensure the counter entity (`TREND_COUNTER_ENTITY`) is valid and initialized
        registry = er.async_get(self.hass)
        existing_state = self.hass.states.get(self._counter_entity_id)

        retries = 5  # Retry limit to stabilize the counter entity
        for attempt in range(retries):
            if existing_state and existing_state.state.isdigit():
                self._trend_counter = int(existing_state.state)
                _LOGGER.debug(
                    "Counter entity initialized with state: %d (after %d retries)",
                    self._trend_counter,
                    attempt + 1,
                )
                break
            elif not existing_state or existing_state.state in ("unknown", "unavailable"):
                _LOGGER.warning(
                    "Counter entity state invalid or unavailable (state: %s) on attempt %d. Retrying...",
                    existing_state.state if existing_state else "None",
                    attempt + 1,
                )
                self.hass.states.async_set(self._counter_entity_id, 0)
                await asyncio.sleep(1)
                existing_state = self.hass.states.get(self._counter_entity_id)
        else:
            _LOGGER.error(
                "Counter entity failed to stabilize after %d retries. Forcing initialization to 0.", retries
            )
            self._trend_counter = 0
            self.hass.states.async_set(self._counter_entity_id, self._trend_counter)

        _LOGGER.debug("Final counter state initialized: %d", self._trend_counter)
        self._state = self._trend_counter
        self.async_write_ha_state()
        _LOGGER.debug("Trend counter reflected in state: %d", self._state)

        # Ensure the manager starts processing
        self._start_task()

    def _initialize_entities(self):
        """Ensure TREND_INTERVAL_ENTITY and TREND_VALUES_ENTITY are initialized with valid states."""
        interval_entity = self.hass.states.get(TREND_INTERVAL_ENTITY)
        steps_entity = self.hass.states.get(TREND_VALUES_ENTITY)

        # Initialize interval entity
        if not interval_entity or interval_entity.state in (None, "unknown", "unavailable"):
            _LOGGER.warning("Interval entity missing or invalid. Initializing to default: %d", DEFAULT_INTERVAL)
            self.hass.states.async_set(TREND_INTERVAL_ENTITY, DEFAULT_INTERVAL)

        # Initialize steps entity
        if not steps_entity or steps_entity.state in (None, "unknown", "unavailable"):
            _LOGGER.warning("Steps entity missing or invalid. Initializing to default: %d", DEFAULT_TREND_VALUES)
            self.hass.states.async_set(TREND_VALUES_ENTITY, DEFAULT_TREND_VALUES)

        _LOGGER.debug(
            "Entities initialized: interval=%s, steps=%s",
            self.hass.states.get(TREND_INTERVAL_ENTITY).state,
            self.hass.states.get(TREND_VALUES_ENTITY).state,
        )

    async def async_update_settings(self, interval=None, steps=None):
        """Update interval and steps dynamically."""
        _LOGGER.debug("Attempting to update settings dynamically: interval=%s, steps=%s", interval, steps)

        # Use current values if not provided
        interval = interval if interval is not None else self._interval
        steps = steps if steps is not None else self._trend_values

        self.hass.states.async_set(TREND_INTERVAL_ENTITY, interval)
        self.hass.states.async_set(TREND_VALUES_ENTITY, steps)

        # Ensure settings are reloaded
        try:
            await self._reload_settings()
            _LOGGER.debug("Settings successfully updated: interval=%s, steps=%s", interval, steps)
        except Exception as e:
            _LOGGER.error("Failed to update settings: %s", e)

    async def _initialize_buffers(self):
        """Initialize trend calculation buffers and ensure counter state stability."""
        _LOGGER.debug("_initialize_buffers called. Current counter: %d", self._trend_counter)

        retries = 5  # Retry limit to stabilize the counter entity
        for attempt in range(retries):
            existing_state = self.hass.states.get(self._counter_entity_id)

            # Handle valid numeric state
            if existing_state and existing_state.state.isdigit():
                self._trend_counter = int(existing_state.state)
                _LOGGER.debug(
                    "Counter entity initialized with state: %d (after %d retries)",
                    self._trend_counter,
                    attempt + 1,
                )
                break

            # Handle invalid or unavailable state
            _LOGGER.warning(
                "Counter entity state invalid or unavailable (state: %s) on attempt %d. Retrying...",
                existing_state.state if existing_state else "None",
                attempt + 1,
            )
            if not existing_state or existing_state.state in ("unknown", "unavailable"):
                self.hass.states.async_set(self._counter_entity_id, 0)
            await asyncio.sleep(1)

        # Final fallback if still invalid after retries
        final_state = self.hass.states.get(self._counter_entity_id)
        if not final_state or not final_state.state.isdigit():
            _LOGGER.error(
                "Counter entity failed to stabilize after %d retries. Forcing initialization to 0.", retries
            )
            self._trend_counter = 0
            self.hass.states.async_set(self._counter_entity_id, self._trend_counter)

        # Reinitialize buffers for all entities
        for entity_id in self._entities:
            if entity_id not in self._buffers:
                self._buffers[entity_id] = []
        _LOGGER.debug("Buffers reinitialized for all entities. Current state: %s", self._buffers)

        _LOGGER.debug("Final counter state initialized: %d", self._trend_counter)

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
        _LOGGER.debug("Restarting the main loop.")

        # Stop the current task
        if self._task:
            _LOGGER.debug("Cancelling the existing main loop task.")
            self._task.cancel()
            try:
                await self._task  # Properly await the cancellation
            except asyncio.CancelledError:
                _LOGGER.debug("Existing main loop task cancelled successfully.")
            self._task = None  # Clear the reference to the old task

        # Clear buffers and counters
        await self._clear_buffers_and_counters()

        # Start the new task
        _LOGGER.debug("Starting a new main loop task.")
        self._start_task()

    async def _clear_buffers_and_counters(self):
        """Clear buffers and reset counters."""
        self._buffers = {entity_id: [] for entity_id in self._entities}
        self._trend_counter = 0
        self.hass.states.async_set(self._counter_entity_id, self._trend_counter)
        _LOGGER.info("Buffers cleared and counters reset.")

    def _start_task(self):
        """Start the main processing loop."""
        if not self._running:
            _LOGGER.debug("Starting the main loop.")
            self._running = True
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._main_loop())
                _LOGGER.debug("Main loop task created: %s", self._task)
            else:
                _LOGGER.warning("Attempted to start a new task, but an existing task is still running.")
        else:
            _LOGGER.debug("Main loop already running. Skipping task creation.")

    async def _update_counter(self, new_value):
        """Safely update the trend counter state."""
        async with self._counter_lock:
            current_state = self.hass.states.get(self._counter_entity_id)

            # Handle valid numeric state
            if current_state and current_state.state.isdigit():
                current_counter = int(current_state.state)
            else:
                _LOGGER.warning(
                    "Counter entity state invalid or unavailable (state: %s). Resetting to 0.",
                    current_state.state if current_state else "None",
                )
                current_counter = 0
                self.hass.states.async_set(self._counter_entity_id, current_counter)

            # Avoid redundant updates
            if current_counter == new_value:
                _LOGGER.debug("Counter value already %d. No update needed.", new_value)
                return

            # Validate the transition
            expected_next_value = (current_counter + 1) % (self._trend_values + 1)
            if new_value != expected_next_value:
                _LOGGER.warning(
                    "Unexpected counter transition: %d -> %d. Adjusting to expected value: %d.",
                    current_counter, new_value, expected_next_value,
                )
                new_value = expected_next_value

            # Safeguard against reset unless explicitly required
            if new_value == 0 and current_counter != self._trend_values:
                _LOGGER.error(
                    "Unexpected reset detected: %d -> 0. Ignoring update.", current_counter
                )
                return

            self._trend_counter = new_value
            self.hass.states.async_set(self._counter_entity_id, self._trend_counter)
            _LOGGER.info("Trend counter updated: %d -> %d", current_counter, self._trend_counter)

    async def _main_loop(self):
        """Main loop for processing trends."""
        while self._running:
            try:
                # Reload settings
                await self._reload_settings()
                _LOGGER.debug("Settings reloaded: interval=%d, trend_values=%d, counter=%d",
                              self._interval, self._trend_values, self._trend_counter)

                # Validate and update trend counter
                current_counter_state = self.hass.states.get(self._counter_entity_id)
                if current_counter_state and current_counter_state.state.isdigit():
                    self._trend_counter = int(current_counter_state.state)
                else:
                    _LOGGER.warning("Counter state is invalid or unavailable. Resetting to default (0).")
                    await self._update_counter(0)

                # Process trends
                await self._process_trends()
                _LOGGER.debug("Processing trends for all entities completed.")

                # Increment and update trend counter
                new_counter_value = (self._trend_counter + 1) % (self._trend_values + 1)
                await self._update_counter(new_counter_value)

            except Exception as e:
                _LOGGER.error("Error in main loop: %s", e)
                _LOGGER.debug("Restarting main loop after exception.")
                await asyncio.sleep(1)  # Pause before restarting the loop

            # Sleep for the specified interval
            await asyncio.sleep(self._interval)

    async def _process_trends(self):
        """Process trend calculations for all configured entities."""
        _LOGGER.debug("Starting trend processing. Current counter: %d", self._trend_counter)

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

            buffer = self._buffers.setdefault(entity_id, [])
            buffer.append(current_value)

            # Enforce buffer size to match trend_values
            if len(buffer) > self._trend_values:
                buffer.pop(0)

            _LOGGER.debug("Buffer for entity %s: %s", entity_id, buffer)

            if self._trend_counter == self._trend_values:
                trend_value = self._calculate_trend(entity_id, buffer)
                sensor_entity_id = f"sensor.bettertrends_{entity_id.replace('.', '_')}"

                if trend_value is not None:
                    self.hass.states.async_set(sensor_entity_id, trend_value)
                    _LOGGER.info("Updated trend for %s: %s", sensor_entity_id, trend_value)

                # Clear the buffer after processing
                self._buffers[entity_id] = []
            else:
                _LOGGER.debug("Buffer for %s is not yet full. Skipping trend update.", entity_id)

    async def _reload_settings(self):
        """Reload settings for interval, steps, and counter."""

        def check_entity_availability():
            """Check if the required entities are available."""
            interval_entity = self.hass.states.get(TREND_INTERVAL_ENTITY)
            steps_entity = self.hass.states.get(TREND_VALUES_ENTITY)
            _LOGGER.debug(
                "Entity availability check: interval=%s, steps=%s",
                interval_entity.state if interval_entity else "None",
                steps_entity.state if steps_entity else "None",
            )
            return (
                interval_entity and interval_entity.state not in (None, "unknown", "unavailable"),
                steps_entity and steps_entity.state not in (None, "unknown", "unavailable"),
            )

        # Ensure entities are initialized with default values if missing
        self._initialize_entities()

        # Wait for entities to stabilize
        interval_ready, steps_ready = check_entity_availability()
        retries = 10  # Retry for up to 10 seconds
        while not (interval_ready and steps_ready) and retries > 0:
            _LOGGER.warning("Waiting for interval and steps entities to stabilize...")
            await asyncio.sleep(1)
            retries -= 1
            interval_ready, steps_ready = check_entity_availability()

        # Final fallback if entities remain unavailable
        if not interval_ready:
            _LOGGER.error("Interval entity unavailable after retries. Falling back to default.")
            self.hass.states.async_set(TREND_INTERVAL_ENTITY, DEFAULT_INTERVAL)

        if not steps_ready:
            _LOGGER.error("Steps entity unavailable after retries. Falling back to default.")
            self.hass.states.async_set(TREND_VALUES_ENTITY, DEFAULT_TREND_VALUES)

        # Reload settings with stabilized states
        interval_entity = self.hass.states.get(TREND_INTERVAL_ENTITY)
        steps_entity = self.hass.states.get(TREND_VALUES_ENTITY)

        self._interval = int(interval_entity.state)
        self._trend_values = int(steps_entity.state)
        _LOGGER.debug(
            "Settings successfully reloaded: interval=%d, trend_values=%d",
            self._interval,
            self._trend_values,
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
        """Dynamically add new entities to the manager and ensure everything is restarted."""
        reset_needed = False
        for entity_id in new_entities:
            if entity_id not in self._entities:
                self._entities.add(entity_id)
                if entity_id not in self._buffers:
                    self._buffers[entity_id] = []  # Initialize an empty buffer
                _LOGGER.info("Added entity %s to BetterTrends.", entity_id)
                reset_needed = True  # Mark reset as needed when new entities are added

        if reset_needed:
            _LOGGER.info("New entities added. Restarting the manager.")
            asyncio.create_task(self._restart_task())

    async def _clear_and_restart(self):
        """Clear all buffers and counters, then restart the manager."""
        _LOGGER.info("Clearing buffers and restarting BetterTrendsManager.")

        # Clear all buffers
        self._buffers = {entity_id: [] for entity_id in self._entities}

        # Reset trend counter
        self._trend_counter = 0
        self.hass.states.async_set(self._counter_entity_id, self._trend_counter)

        # Restart the task to reflect the changes
        await self._restart_task()
        _LOGGER.info("Buffers cleared and counters reset. Manager restarted.")

    def remove_entity(self, entity_id: str):
        """Dynamically remove an entity from the manager."""
        if entity_id in self._entities:
            self._entities.remove(entity_id)
            if entity_id in self._buffers:
                del self._buffers[entity_id]
            _LOGGER.info("Removed entity %s from BetterTrends.", entity_id)

    @callback
    def monitor_trend_counter(event):
        """Log every state change for the counter entity."""
        entity_id = TREND_COUNTER_ENTITY
        if event.data.get("entity_id") == entity_id:
            old_state = event.data.get("old_state").state if event.data.get("old_state") else "None"
            new_state = event.data.get("new_state").state if event.data.get("new_state") else "None"
            _LOGGER.info("Trend counter state changed externally: %s -> %s", old_state, new_state)
            
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
        current_state = self.hass.states.get(self.unique_id)
        _LOGGER.debug(
            "async_update called for %s. Current state: %s. State managed by BetterTrendsManager.",
            self._entity_id,
            current_state.state if current_state else "None",
        )
        # Log if state changes unexpectedly
        if current_state and current_state.state == "0":
            _LOGGER.warning(
                "Unexpected reset detected during async_update for %s. Current state: %s",
                self._entity_id,
                current_state.state,
            )