from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES, TREND_INTERVAL_ENTITY, TREND_VALUES_ENTITY, \
    TREND_COUNTER_ENTITY
import logging
from homeassistant.helpers import entity_registry as er  # Ensure this import exists
import traceback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends numbers from a config entry."""
    try:
        registry = er.async_get(hass)

        # Add interval entity if not found
        if not registry.async_get(TREND_INTERVAL_ENTITY):
            interval_entity = TrendNumber(
                "BetterTrends Interval",
                TREND_INTERVAL_ENTITY,
                DEFAULT_INTERVAL,
                5,
                9999,
            )
            async_add_entities([interval_entity])

        # Add steps entity if not found
        if not registry.async_get(TREND_VALUES_ENTITY):
            steps_entity = TrendNumber(
                "BetterTrends Steps",
                TREND_VALUES_ENTITY,
                DEFAULT_TREND_VALUES,
                1,
                1000,
            )
            async_add_entities([steps_entity])

        # Add counter entity if not found
        if not registry.async_get(TREND_COUNTER_ENTITY):
            current_step_entity = TrendNumber(
                "BetterTrends Current Step",
                TREND_COUNTER_ENTITY,
                0,
                0,
                1000,
            )
            async_add_entities([current_step_entity])
    except Exception as e:
        _LOGGER.error(f"Error setting up entities: {traceback.format_exc()}")


class TrendNumber(NumberEntity):
    """A numeric entity representing a configurable value."""

    def __init__(self, name, unique_id, initial_value, min_value, max_value, suffix=""):
        self._attr_name = name
        self._attr_unique_id = f"{unique_id}{suffix}"  # Use suffix for unique ID generation
        self._attr_native_value = initial_value
        self._attr_min_value = min_value
        self._attr_max_value = max_value
        self._attr_step = 1  # Step size for adjustments
        self._attr_mode = NumberMode.BOX  # Editable field in the UI

    async def async_added_to_hass(self):
        """Set initial state when added to hass."""
        _LOGGER.info(f"{self._attr_name} added to Home Assistant with initial value: {self._attr_native_value}")
        _LOGGER.debug(
            f"Re-initializing {self._attr_name}: "
            f"unique_id={self._attr_unique_id}, min_value={self._attr_min_value}, max_value={self._attr_max_value}, "
            f"current_value={self._attr_native_value}"
        )
        self.async_write_ha_state()

    @property
    def unique_id(self):
        """Return a truly unique ID for the number entity."""
        return self._attr_unique_id

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

        _LOGGER.debug(f"Setting {self._attr_name} from {self._attr_native_value} to {value}")
        self._attr_native_value = int(value)
        self.async_write_ha_state()
        _LOGGER.info(f"{self._attr_name} updated to {self._attr_native_value}")
