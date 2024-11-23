from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors and input numbers from a config entry."""
    user_entities = entry.data.get("entities", [])

    # Ensure input_number entities exist for interval and steps
    await async_create_input_number(hass, "trend_sensor_interval", "Trend Sensor Interval", 1, 3600, DEFAULT_INTERVAL)
    await async_create_input_number(hass, "trend_sensor_steps", "Trend Sensor Steps", 1, 100, DEFAULT_TREND_VALUES)

    # Get the input_number entities
    interval_entity_id = "input_number.trend_sensor_interval"
    steps_entity_id = "input_number.trend_sensor_steps"

    # Create trend sensors for user-provided entities
    trend_sensors = [
        BetterTrendsSensor(entity_id, hass, interval_entity_id, steps_entity_id)
        for entity_id in user_entities
    ]

    # Add all trend sensors to Home Assistant
    async_add_entities(trend_sensors, update_before_add=True)


async def async_create_input_number(hass, object_id, name, min_value, max_value, initial_value):
    """Helper to create an input_number entity if it doesn't already exist."""
    registry = await hass.helpers.entity_registry.async_get_registry()
    if f"input_number.{object_id}" not in registry.entities:
        _LOGGER.info(f"Creating input_number.{object_id}")
        await hass.services.async_call(
            "input_number",
            "create",
            {
                "name": name,
                "min": min_value,
                "max": max_value,
                "step": 1,
                "mode": "box",
                "initial": initial_value,
                "unique_id": object_id,
            },
        )
        
        
class TrendNumber(NumberEntity):
    """A numeric entity representing a configurable value."""

    def __init__(self, name, unique_id, initial_value, min_value, max_value):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_value = initial_value  # Use native_value instead of value
        self._attr_min_value = min_value
        self._attr_max_value = max_value
        self._attr_step = 1
        self._attr_mode = NumberMode.BOX  # Allow direct user input in the UI

    @property
    def native_value(self):
        """Return the current value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float):
        """Set a new value."""
        self._attr_native_value = int(value)
        self.async_write_ha_state()
        _LOGGER.info(f"{self._attr_name} updated to {self._attr_native_value}")


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, hass, interval_entity_id, steps_entity_id):
        self._entity_id = entity_id
        self.hass = hass
        self._interval_entity_id = interval_entity_id
        self._steps_entity_id = steps_entity_id
        self._values = []
        self._state = None
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        """Return the current trend value."""
        return self._state

    async def async_added_to_hass(self):
        """Start periodic data collection when the sensor is added."""
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        """Collect entity state at regular intervals and calculate the trend."""
        while True:
            try:
                # Fetch interval and steps dynamically from input_number entities
                interval_state = self.hass.states.get(self._interval_entity_id)
                steps_state = self.hass.states.get(self._steps_entity_id)
                interval = int(interval_state.state) if interval_state else 60
                steps = int(steps_state.state) if steps_state else 10

                state = self.hass.states.get(self._entity_id)
                if state:
                    try:
                        value = float(state.state)
                        self._handle_new_value(value, steps)
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
            await asyncio.sleep(interval)

    def _handle_new_value(self, value, steps):
        """Handle a new value and calculate the trend."""
        if not self._values:
            self._state = 0.0
        else:
            self._add_value(value, steps)
            if len(self._values) == steps:
                self._state = self._calculate_trend()

    def _add_value(self, value, steps):
        """Maintain a fixed-length buffer."""
        if len(self._values) >= steps:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        """Calculate the trend based on the rolling buffer."""
        total = sum(self._values)
        return round(total / len(self._values), 2)
