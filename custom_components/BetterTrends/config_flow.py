import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step to collect the first sensor."""
        if user_input is not None:
            # Store the initial sensor in the configuration data
            self.sensors.append(user_input["sensor_0"])
            return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        # Define the schema for the initial setup form (requesting the first sensor)
        data_schema = vol.Schema({
            vol.Required("sensor_0", default=""): str  # Field to enter the first sensor
        })

        # Show the form with the schema
        return self.async_show_form(step_id="user", data_schema=data_schema)
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to modify sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors after setup."""
        if user_input is not None:
            # Collect the sensors from the options form
            sensors = [sensor.strip() for sensor in user_input.values() if sensor.startswith("sensor_") and sensor]
            new_options = {"sensors": sensors}
            self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

            # Reload the entry to apply changes immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show the form initially to configure sensors
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema()
        )

    def _build_options_schema(self):
        """Build schema dynamically for editing sensors."""
        sensors = self.config_entry.options.get("sensors", [])
        
        # Create schema for each sensor and add an extra field for adding a new sensor
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field to add a new sensor

        return vol.Schema(schema)
