from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])

    # Create numeric entities for interval and steps
    interval_entity = TrendNumber(
        "Trend Sensor Interval",
        "trend_sensor_interval",
        DEFAULT_INTERVAL,
        1,
        3600,
    )
    steps_entity = TrendNumber(
        "Trend Sensor Steps",
        "trend_sensor_steps",
        DEFAULT_TREND_VALUES,
        1,
        100,
    )

    _LOGGER.debug("Adding TrendNumber entities: interval_entity and steps_entity")

    # Add interval and step entities to Home Assistant
    async_add_entities([interval_entity, steps_entity], update_before_add=True)

    # Create trend sensors for user-provided entities
    trend_sensors = [
        BetterTrendsSensor(entity_id, hass, interval_entity, steps_entity)
        for entity_id in user_entities
    ]
    async_add_entities(trend_sensors, update_before_add=True)


class TrendNumber(NumberEntity):
    """A numeric entity representing a configurable value."""

    def __init__(self, name, unique_id, initial_value, min_value, max_value):
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_native_value = initial_value
        self._attr_min_value = min_value
        self._attr_max_value = max_value
        self._attr_step = 1  # Step size for adjustments
        self._attr_mode = NumberMode.BOX  # Editable field in the UI

    @property
    def native_value(self):
        """Return the current value or a default if invalid."""
        if self._attr_native_value is None or self._attr_native_value < self._attr_min_value:
            return self._attr_min_value
        return self._attr_native_value

    async def async_set_native_value(self, value: float):
        """Set a new value."""
        if value < self._attr_min_value or value > self._attr_max_value:
            _LOGGER.warning(
                f"Attempted to set {self._attr_name} to {value}, which is out of bounds. "
                f"Valid range: {self._attr_min_value}-{self._attr_max_value}."
            )
            return

        self._attr_native_value = int(value)
        self.async_write_ha_state()
        _LOGGER.info(f"{self._attr_name} updated to {self._attr_native_value}")


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, hass, interval_entity: TrendNumber, steps_entity: TrendNumber):
        self._entity_id = entity_id
        self.hass = hass
        self._interval_entity = interval_entity
        self._steps_entity = steps_entity
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
                # Fetch interval and steps dynamically from TrendNumber entities
                interval = self._interval_entity.native_value
                steps = self._steps_entity.native_value

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

            # Ensure interval is valid before calling asyncio.sleep
            if interval is None or interval <= 0:
                _LOGGER.error(f"Invalid interval: {interval}. Defaulting to 60 seconds.")
                interval = 60

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
