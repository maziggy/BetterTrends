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

    # Add your existing async_step_user, async_step_add_more, and other methods here

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
            # Validate the interval
            interval = user_input.get("update_interval", INTERVAL_DEFAULT)
            if not (1 <= interval <= 60):
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_options_schema(),
                    errors={"update_interval": "invalid_interval"}
                )

            # Update the options with the validated interval and sensors
            sensors = [sensor.strip() for sensor in user_input.values() if sensor.startswith("sensor_") and sensor]
            new_options = {"sensors": sensors, "update_interval": interval}
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

            # Reload the entry to apply changes immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show the form initially
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema()
        )

    def _build_options_schema(self):
        """Build schema dynamically for sensors and interval option."""
        sensors = self.config_entry.options.get("sensors", [])
        interval = self.config_entry.options.get("update_interval", INTERVAL_DEFAULT)

        # Create schema for each sensor and add an extra field for a new sensor
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field to add a new sensor
        schema[vol.Required("update_interval", default=interval)] = vol.All(vol.Coerce(int), vol.Range(min=1, max=60))

        return vol.Schema(schema)
