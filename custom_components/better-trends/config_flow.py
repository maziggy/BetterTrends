from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .const import DOMAIN, DEFAULT_INTERVAL, DEFAULT_TREND_VALUES

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BetterTrends."""

    VERSION = 1

    def __init__(self):
        self.entities = []  # Store entities dynamically as the user adds them

    async def async_step_user(self, user_input=None):
        """Handle the initial step of the config flow."""
        errors = {}

        if user_input is not None:
            new_entity = user_input.get("new_entity")

            # If the user didn't leave the field empty
            if new_entity:
                # Validate the entity
                if new_entity in self.hass.states.async_entity_ids("sensor"):
                    self.entities.append(new_entity)
                else:
                    errors["new_entity"] = "invalid_entity"
            else:
                # Finish if the user left the field empty
                if self.entities:
                    return self.async_create_entry(
                        title="BetterTrends",
                        data={
                            "entities": self.entities,
                            "trend_values": user_input.get("trend_values"),
                            "interval": user_input.get("interval"),
                        },
                    )
                else:
                    errors["new_entity"] = "no_entities"

        # Create the form schema
        schema = vol.Schema(
            {
                vol.Optional("new_entity"): str,
                vol.Required("trend_values", default=DEFAULT_TREND_VALUES): vol.Coerce(int),
                vol.Required("interval", default=DEFAULT_INTERVAL): vol.Coerce(int),
            }
        )

        # Display the form
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
