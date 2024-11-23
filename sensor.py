from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .utils import calculate, get_ha_data, set_ha_data
from .const import DOMAIN

class TrendSensor(SensorEntity):
    """A sensor to calculate trends for specified entities."""

    def __init__(self, hass, api_url, token, entity_id, trend_values, metrics):
        self.hass = hass
        self._api_url = api_url
        self._token = token
        self._entity_id = entity_id
        self._trend_values = trend_values
        self._metrics = metrics
        self._attr_name = f"{entity_id} Trend"
        self._attr_unique_id = f"{DOMAIN}_{entity_id}_trend"
        self._attr_state = None

    async def async_update(self):
        """Fetch the latest state and calculate trends."""
        # Fetch current value
        last = await get_ha_data(self.hass, self._api_url, self._token, self._entity_id)
        if last is not None:
            # Update metrics
            self._metrics[f'value{len(self._metrics)}'] = last
            # Calculate trend
            self._attr_state = calculate(self._metrics, last, self._trend_values)
            # Push new calculated value to Home Assistant
            await set_ha_data(self.hass, self._api_url, self._token, self._entity_id, self._attr_state)
