from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .const import DOMAIN

# Example schema for configuration input
CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("entities", default=[]): cv.multi_select(["sensor.example_1", "sensor.example_2"]),
        vol.Optional("trend_values", default=5): vol.Coerce(int),
        vol.Optional("interval", default=60): vol.Coerce(int),
    }
)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BetterTrends."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="BetterTrends", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA
        )
