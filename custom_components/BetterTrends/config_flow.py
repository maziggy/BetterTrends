import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

INTERVAL_DEFAULT = 5  # Default to 5 minutes, can be changed

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            # Create the config entry with the user inputs
            return self.async_create_entry(title="Better Trends", data=user_input)

        # Show a form if user_input is None
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to modify sensors and update interval after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors and interval."""
        if user_input is not None:
            interval = user_input.get("update_interval", INTERVAL_DEFAULT)

            sensors = [sensor.strip() for sensor in user_input.values() if sensor.startswith("sensor_") and sensor]
            new_options = {"sensors": sensors, "update_interval": interval}
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema()
        )

    def _build_options_schema(self):
        sensors = self.config_entry.options.get("sensors", [])
        interval = self.config_entry.options.get("update_interval", INTERVAL_DEFAULT)

        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str
        schema[vol.Required("update_interval", default=interval)] = vol.All(vol.Coerce(int), vol.Range(min=1, max=60))

        return vol.Schema(schema)
