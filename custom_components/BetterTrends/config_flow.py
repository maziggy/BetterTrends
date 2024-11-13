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
        """Initial setup to collect the first sensor and continue adding more."""
        if user_input is not None:
            sensor_id = user_input["sensor_0"].strip()

            # Add the first sensor to the list
            if sensor_id not in self.sensors:
                self.sensors.append(sensor_id)
                _LOGGER.debug("Initial sensor added: %s", sensor_id)

            # Move to the next step to add more sensors
            return await self.async_step_add_more()

        # Show the form to enter the first sensor
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("sensor_0", default=""): str})
        )

    async def async_step_add_more(self, user_input=None):
        """Step to add additional sensors or finish setup."""
        if user_input is not None:
            new_sensor = user_input.get("sensor_next", "").strip()
            if new_sensor and new_sensor not in self.sensors:
                self.sensors.append(new_sensor)
                _LOGGER.debug("Additional sensor added: %s", new_sensor)

            # Check if user chose to finish
            if user_input.get("finish", False):
                _LOGGER.debug("Final sensor list saved in options: %s", self.sensors)
                # Create the entry with the collected sensors in options
                return self.async_create_entry(title="Better Trends", data={}, options={"sensors": self.sensors})

        # Show form to add more sensors or choose to finish
        return self.async_show_form(
            step_id="add_more",
            data_schema=vol.Schema({
                vol.Optional("sensor_next", default=""): str,  # Field to add another sensor
                vol.Optional("finish", default=False): bool   # Checkbox to finish setup
            })
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to modify sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors."""
        if user_input is not None:
            # Collect all sensors from the options form
            sensors = [sensor.strip() for sensor in user_input.values() if sensor]
            _LOGGER.debug("Updating sensors in options flow: %s", sensors)

            # Update config entry with unique sensors
            self.hass.config_entries.async_update_entry(self.config_entry, options={"sensors": sensors})
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Retrieve existing sensors from options
        sensors = self.config_entry.options.get("sensors", [])
        return self.async_show_form(step_id="init", data_schema=self._build_options_schema(sensors))

    def _build_options_schema(self, sensors):
        """Builds schema dynamically to manage sensors in options."""
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Add a field for a new sensor
        return vol.Schema(schema)
