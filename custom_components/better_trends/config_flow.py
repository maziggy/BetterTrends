from homeassistant import config_entries
import voluptuous as vol
from homeassistant.helpers import selector
from .const import DOMAIN


class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BetterTrends."""

    VERSION = 1

    def __init__(self):
        self.entities = []  # Store entities dynamically added by the user

    async def async_step_user(self, user_input=None):
        """Handle the step where entities are added."""
        errors = {}

        # Preload previously configured entities
        if not self.entities:
            existing_entries = [
                entry for entry in self.hass.config_entries.async_entries(DOMAIN)
            ]
            if existing_entries:
                self.entities = existing_entries[0].data.get("entities", [])

        if user_input is not None:
            new_entity = user_input.get("entity")

            if new_entity:
                # Validate the entered entity
                if new_entity in self.hass.states.async_entity_ids("sensor"):
                    if new_entity not in self.entities:
                        self.entities.append(new_entity)  # Add to the list of valid entities
                else:
                    errors["entity"] = "invalid_entity"
            else:
                # Finalize configuration if no new entity is provided
                if self.entities:
                    existing_entries = [
                        entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                    ]
                    if existing_entries:
                        entry = existing_entries[0]

                        # Merge existing entities with new ones
                        updated_entities = list(set(entry.data["entities"] + self.entities))
                        new_data = {**entry.data, "entities": updated_entities}

                        # Update the entry with the new data
                        self.hass.config_entries.async_update_entry(entry, data=new_data)

                        # Reload the entry to apply changes
                        await self.hass.config_entries.async_reload(entry.entry_id)
                        return self.async_abort(reason="reconfigure_successful")
                    else:
                        # Create a new entry if none exists
                        return self.async_create_entry(
                            title="BetterTrends",
                            data={"entities": self.entities},
                        )

                errors["entity"] = "no_entities"

        # Build the form schema dynamically
        schema = self._build_schema()

        # Show the form with errors (if any)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _build_schema(self):
        """Build the schema with a selector for entity search."""
        schema = {}

        # Add previously entered entities as non-editable fields
        for i, entity in enumerate(self.entities):
            schema[vol.Optional(f"entity_{i}", default=entity)] = str

        # Add an entity selector for the next entity
        schema[vol.Optional("entity")] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        )

        return vol.Schema(schema)
