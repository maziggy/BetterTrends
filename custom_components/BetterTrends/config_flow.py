import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

INTERVAL_DEFAULT = 5  # Default interval in minutes
STEPS_DEFAULT = 10  # Default number of steps

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

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
            # Validate inputs and save options
            interval = user_input.get("update_interval", INTERVAL_DEFAULT)
            steps = user_input.get("steps", STEPS_DEFAULT)

            sensors = [sensor.strip() for sensor in user_input.values() if sensor.startswith("sensor_") and sensor]
            new_options = {"sensors": sensors, "update_interval": interval, "steps": steps}
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

            # Reload the entry to apply changes immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show the form initially with default or stored values
        interval = self.config_entry.options.get("update_interval", INTERVAL_DEFAULT)
        steps = self.config_entry.options.get("steps", STEPS_DEFAULT)
        
        schema = {
            vol.Required("update_interval", default=interval): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Required("steps", default=steps): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
        }
        
        # Add sensor fields as in the previous flow
        sensors = self.config_entry.options.get("sensors", [])
        for i, sensor in enumerate(sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field for adding a new sensor

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema)
        )
