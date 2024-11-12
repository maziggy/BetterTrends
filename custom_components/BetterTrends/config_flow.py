import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle initial step to create entry with test option data."""
        if user_input is not None:
            _LOGGER.debug("Creating entry with test data")
            # Create a config entry with a test option
            return self.async_create_entry(title="Better Trends Test", data={}, options={"test_key": "test_value"})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("dummy_field", default="test"): str})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to verify options are saved and accessible."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Allow viewing and modifying the test option."""
        if user_input is not None:
            # Update test_key in options
            self.hass.config_entries.async_update_entry(self.config_entry, options={"test_key": user_input["test_key"]})
            _LOGGER.debug("Updated test_key in options: %s", user_input["test_key"])
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        test_value = self.config_entry.options.get("test_key", "test_value")
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("test_key", default=test_value): str})
        )
