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

    async def async_step_user(self, user_input=None):
        """Initial setup to collect the first sensor."""
        if user_input is not None:
            sensor_id = user_input["sensor_0"].strip()

            # Validate sensor
            if not await self._validate_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._build_schema(),
                    errors={"sensor_0": "invalid_sensor"}
                )

            # Save to options immediately
            _LOGGER.debug("Saving initial sensor in options: %s", sensor_id)
            return self.async_create_entry(title="Better Trends", data={}, options={"sensors": [sensor_id]})

        return self.async_show_form(step_id="user", data_schema=self._build_schema())

    async def _validate_sensor(self, sensor_id):
        """Check if a sensor exists in the entity registry."""
        if not sensor_id.startswith("sensor."):
            return False
        entity_registry = async_get(self.hass)
        return entity_registry.async_is_registered(sensor_id)

    def _build_schema(self):
        """Build schema for sensor input."""
        return vol.Schema({vol.Required("sensor_0", default=""): str})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to manage additional sensors."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options to add/remove sensors."""
        if user_input is not None:
            # Collect sensors from user input
            sensors = [sensor.strip() for sensor in user_input.values() if sensor]
            unique_sensors = list(dict.fromkeys(sensors))  # Remove duplicates

            # Log and save to options
            _LOGGER.debug("Updating sensors in options: %s", unique_sensors)
            self.hass.config_entries.async_update_entry(self.config_entry, options={"sensors": unique_sensors})

            # Reload the entry to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Prepopulate sensors from options
        sensors = self.config_entry.options.get("sensors", [])
        return self.async_show_form(step_id="init", data_schema=self._build_options_schema(sensors))

    def _build_options_schema(self, sensors):
        """Build schema dynamically for adding/removing sensors."""
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str
        return vol.Schema(schema)
