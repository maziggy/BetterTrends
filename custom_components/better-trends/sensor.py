from homeassistant.core import HomeAssistant, callback
from homeassistant.components.sensor import SensorEntity  # Import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("SensorEntity successfully imported and sensor.py loaded.")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up BetterTrends sensors from a config entry."""
    user_entities = entry.data.get("entities", [])
    interval = DEFAULT_INTERVAL
    trend_values = DEFAULT_TREND_VALUES

    new_sensors = []

    for entity_id in user_entities:
        new_sensors.append(BetterTrendsSensor(entity_id, trend_values, interval, hass))

    new_sensors.append(EditableIntervalSensor(hass, entry))
    new_sensors.append(EditableStepsSensor(hass, entry))

    async_add_entities(new_sensors, update_before_add=True)


class BetterTrendsSensor(SensorEntity):
    """A sensor to calculate trends for user-provided entities."""

    def __init__(self, entity_id, trend_values, interval, hass):
        self._entity_id = entity_id
        self._trend_values = trend_values
        self._interval = interval
        self._values = []
        self._last_fetched_value = None
        self._state = None
        self.hass = hass
        self._attr_name = f"Trend {entity_id}"
        self._attr_unique_id = f"better_trends_{entity_id}"

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        self.hass.loop.create_task(self._collect_data())

    async def _collect_data(self):
        while True:
            try:
                state = self.hass.states.get(self._entity_id)
                if state:
                    try:
                        value = float(state.state)
                        self._handle_new_value(value)
                    except ValueError:
                        self._state = None
                        _LOGGER.warning(f"Invalid state for {self._entity_id}: {state.state}")
                else:
                    self._state = None
                    _LOGGER.warning(f"Entity {self._entity_id} not found.")
            except Exception as e:
                self._state = None
                _LOGGER.error(f"Error collecting data for {self._entity_id}: {e}")

            self.async_write_ha_state()
            await asyncio.sleep(self._interval)

    def _handle_new_value(self, value):
        if not self._values:
            self._state = 0.0
            self._last_fetched_value = value
        else:
            self._add_value(value)
            if len(self._values) == self._trend_values:
                self._state = self._calculate_trend()

    def _add_value(self, value):
        if len(self._values) >= self._trend_values:
            self._values.pop(0)
        self._values.append(value)

    def _calculate_trend(self):
        total = sum(self._values)
        return round(total / self._trend_values, 1)


class EditableIntervalSensor(SensorEntity):
    """A sensor representing the editable interval."""

    def __init__(self, hass, entry):
        self._state = DEFAULT_INTERVAL
        self.hass = hass
        self._entry = entry
        self._input_number_entity = "input_number.trend_sensor_interval"
        self._attr_name = "Trend Sensor Interval"
        self._attr_unique_id = "trend_sensor_interval"

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        await self._ensure_input_number_exists(
            self._input_number_entity, "Trend Sensor Interval", 1, 3600, DEFAULT_INTERVAL
        )
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)
        self._update_state_from_input_number()

    async def _ensure_input_number_exists(self, entity_id, name, min_value, max_value, initial_value):
        if not self.hass.states.get(entity_id):
            await self.hass.services.async_call(
                "input_number",
                "create",
                {
                    "entity_id": entity_id,
                    "name": name,
                    "min": min_value,
                    "max": max_value,
                    "step": 1,
                    "initial": initial_value,
                },
            )

    @callback
    def _handle_state_change(self, event):
        if event.data.get("entity_id") == self._input_number_entity:
            self._update_state_from_input_number()

    def _update_state_from_input_number(self):
        state = self.hass.states.get(self._input_number_entity)
        if state:
            try:
                self._state = int(float(state.state))
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning(f"Invalid value for {self._input_number_entity}: {state.state}")


class EditableStepsSensor(SensorEntity):
    """A sensor representing the editable steps."""

    def __init__(self, hass, entry):
        self._state = DEFAULT_TREND_VALUES
        self.hass = hass
        self._entry = entry
        self._input_number_entity = "input_number.trend_sensor_steps"
        self._attr_name = "Trend Sensor Steps"
        self._attr_unique_id = "trend_sensor_steps"

    @property
    def native_value(self):
        return self._state

    async def async_added_to_hass(self):
        await self._ensure_input_number_exists(
            self._input_number_entity, "Trend Sensor Steps", 1, 100, DEFAULT_TREND_VALUES
        )
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)
        self._update_state_from_input_number()

    async def _ensure_input_number_exists(self, entity_id, name, min_value, max_value, initial_value):
        if not self.hass.states.get(entity_id):
            await self.hass.services.async_call(
                "input_number",
                "create",
                {
                    "entity_id": entity_id,
                    "name": name,
                    "min": min_value,
                    "max": max_value,
                    "step": 1,
                    "initial": initial_value,
                },
            )

    @callback
    def _handle_state_change(self, event):
        if event.data.get("entity_id") == self._input_number_entity:
            self._update_state_from_input_number()

    def _update_state_from_input_number(self):
        state = self.hass.states.get(self._input_number_entity)
        if state:
            try:
                self._state = int(float(state.state))
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning(f"Invalid value for {self._input_number_entity}: {state.state}")
