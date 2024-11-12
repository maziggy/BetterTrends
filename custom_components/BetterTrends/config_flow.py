import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Initial setup to collect the first sensor and store it in options."""
        if user_input is not None:
            sensor_id = user_input["sensor_0"].strip()

            # Log and save the initial sensor in options immediately
            _LOGGER.debug("Creating entry with sensor in options: %s", sensor_id)
            return self.async_create_entry(title="Better Trends", data={}, options={"sensors": [sensor_id]})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("sensor_0", default=""): str})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to add additional sensors."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Options flow to view and modify the sensors in options."""
        if user_input is not None:
            # Collect all sensors entered by the user
            sensors = [sensor.strip() for sensor in user_input.values() if sensor]
            _LOGGER.debug("Updating sensors in options: %s", sensors)

            # Update the options entry with sensors
            self.hass.config_entries.async_update_entry(self.config_entry, options={"sensors": sensors})
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Retrieve existing sensors from options
        sensors = self.config_entry.options.get("sensors", [])
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema(sensors)
        )

    def _build_options_schema(self, sensors):
        """Dynamically builds the options schema to manage sensors."""
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str
        return vol.Schema(schema)
