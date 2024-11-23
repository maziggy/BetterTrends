from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .const import DOMAIN, CONF_ENTITIES

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Trend Calculation", data=user_input)

        available_entities = await self._get_available_entities()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_ENTITIES, default=[]): cv.multi_select(available_entities)
            })
        )

    async def _get_available_entities(self):
        """Retrieve a list of all entities from Home Assistant."""
        return {
            entity_id: entity_id
            for entity_id in self.hass.states.async_entity_ids()
        }
