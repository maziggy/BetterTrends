from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors."""
    entities = entry.data["entities"]

    # Create sensor entities for each entity in the config
    trend_sensors = [BetterTrendsSensor(entity_id) for entity_id in entities]
    async_add_entities(trend_sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends."""

    def __init__(self, entity_id):
        self._entity_id = entity_id
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"
        self._state = None

    @property
    def native_value(self):
        """Return the current state."""
        return self._state

    async def async_update(self):
        """Fetch the latest state from the monitored entity."""
        state = self.hass.states.get(self._entity_id)
        if state is not None:
            self._state = float(state.state)  # Convert state to a float for trend calculation
