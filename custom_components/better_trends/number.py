from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends numbers from a config entry."""
    #_LOGGER.debug("Initializing TrendNumber entities")

    try:
        # Create numeric entities for interval, steps, and current step
        interval_entity = TrendNumber(
            "Trend Sensor Interval",
            f"{entry.entry_id}_trend_sensor_interval",
            DEFAULT_INTERVAL,
            5,
            9999,
        )
        steps_entity = TrendNumber(
            "Trend Sensor Steps",
            f"{entry.entry_id}_trend_sensor_steps",
            DEFAULT_TREND_VALUES,
            1,
            1000,
        )
        current_step_entity = TrendNumber(
            "Trend Sensor Current Step",
            f"{entry.entry_id}_trend_sensor_current_step",
            0,  # Initial value should be 0 for the current step
            0,
            1000,
        )

        #_LOGGER.debug("Adding TrendNumber entities: interval_entity, steps_entity, and current_step_entity.")
        async_add_entities([interval_entity, steps_entity, current_step_entity], update_before_add=True)
        #_LOGGER.debug("Entities added successfully")
    except Exception as e:
        _LOGGER.error(f"Error setting up entities: {e}")

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

    async def async_added_to_hass(self):
        """Set initial state when added to hass."""
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the current value."""
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