import voluptuous as vol
from homeassistant import config_entries
import logging

_LOGGER = logging.getLogger(__name__)

class TestPersistenceConfigFlow(config_entries.ConfigFlow, domain="test_persistence"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step to create entry with test options data."""
        if user_input is not None:
            # Immediately set options in entry data to test persistence
            options = {"test_key": "test_value"}
            _LOGGER.debug("Attempting to create entry with options: %s", options)

            # Create the config entry with options
            entry = self.async_create_entry(
                title="Test Entry",
                data={}, 
                options=options
            )

            _LOGGER.debug("Entry created with options: %s", options)
            return entry

        # Show form if no user input yet
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("dummy_field", default=""): str
            })
        )

    @staticmethod
    @config_entries.HANDLERS.register("test_persistence")
    def async_get_options_flow(config_entry):
        return TestPersistenceOptionsFlow(config_entry)


class TestPersistenceOptionsFlow(config_entries.OptionsFlow):
    """Manage options for Test Persistence."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        _LOGGER.debug("Entered options flow for Test Persistence.")

        if user_input is not None:
            options = {"test_key": "updated_value"}
            _LOGGER.debug("Updating entry with options: %s", options)

            # Update the options in the config entry
            self.hass.config_entries.async_update_entry(self.config_entry, options=options)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        options_schema = vol.Schema({
            vol.Required("test_key", default=self.config_entry.options.get("test_key", "test_value")): str
        })

        return self.async_show_form(step_id="init", data_schema=options_schema)
