from homeassistant.components.sensor import SensorEntity
from .metrics import calculate_trends
from .const import DOMAIN, SENSOR_SUFFIX

from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_entities):
    sensors = config_entry.options.get("sensors", config_entry.data.get("sensors")).split(",")

    async_add_entities([BetterTrends(api_url, api_token, sensor.strip()) for sensor in sensors], True)

class TrendSensor(SensorEntity):
    def __init__(self, hass, sensor_id):
        self.hass = hass
        self._sensor_id = sensor_id
        self._state = None
        self._attr_name = f"BetterTrend for {sensor_id}"

    @property
    def state(self):
        return self._state

    async def async_update(self):
        trend_data = calculate_trends(self.hass, self._sensor_id)
        self._state = trend_data.get("trend_value") if trend_data else None

class LastSensor(SensorEntity):
    def __init__(self, hass, sensor_id):
        self._state = None
        self._sensor_id = sensor_id
        self.entity_id = f"sensor.{sensor_id}{SENSOR_SUFFIX}"
        self._attr_name = f"{sensor_id} Last"
        self._attributes = {}

        async_track_state_change(
            hass, sensor_id, self._async_state_changed_listener
        )

    async def _async_state_changed_listener(self, entity_id, old_state, new_state):
        if new_state:
            self._state = new_state.state
            self._attributes = new_state.attributes
            self.async_write_ha_state()

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes
