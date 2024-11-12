import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.entity_registry import async_get
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Initial setup for first sensor."""
        _LOGGER.debug("Starting initial setup step.")
        if user_input is not None:
            sensor_id = user_input["sensor_0"].strip()

            # Validate the sensor and add to sensors list
            if await self._validate_sensor(sensor_id):
                if sensor_id not in self.sensors:
                    self.sensors.append(sensor_id)
                    _LOGGER.debug("Sensor added to list: %s", sensor_id)

                # Immediately create entry for each sensor added
                entry = self.async_create_entry(title="Better Trends", data={}, options={"sensors": self.sensors})
                _LOGGER.debug("Created entry with sensors: %s", entry.options)
                return entry
            else:
                _LOGGER.debug("Invalid sensor ID provided: %s", sensor_id)
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._build_initial_schema(),
                    errors={"sensor_0": "invalid_sensor"}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_initial_schema()
        )

    async def _validate_sensor(self, sensor_id):
        """Check if sensor ID exists in the registry."""
        if not sensor_id.startswith("sensor."):
            return False
        entity_registry = async_get(self.hass)
        exists = entity_registry.async_is_registered(sensor_id)
        _LOGGER.debug("Sensor %s validation result: %s", sensor_id, exists)
        return exists

    def _build_initial_schema(self):
        """Schema to add first sensor."""
        return vol.Schema({
            vol.Required("sensor_0", default=""): str
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to edit sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to modify sensors."""
        _LOGGER.debug("Entering options flow step.")

        if user_input is not None:
            sensors = [sensor.strip() for sensor in user_input.values() if sensor]
            _LOGGER.debug("Updating sensors in options: %s", sensors)

            # Immediately update the config entry
            self.hass.config_entries.async_update_entry(self.config_entry, options={"sensors": sensors})
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        sensors = self.config_entry.options.get("sensors", [])
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema(sensors)
        )

    def _build_options_schema(self, sensors):
        """Build schema dynamically for editing sensors in options."""
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str
        return vol.Schema(schema)
