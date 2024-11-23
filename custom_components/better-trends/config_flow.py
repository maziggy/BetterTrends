from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BetterTrends."""

    VERSION = 1

    def __init__(self):
        self.entities = []  # Store entities dynamically added by the user

    async def async_step_user(self, user_input=None):
        """Handle the step where entities are added."""
        errors = {}

        if user_input is not None:
            # Dynamic labeling for the entity field based on the number of entities entered
            if len(self.entities) < 2:
                new_entity = user_input.get(f"entity_{len(self.entities)}", "")
            else:
                new_entity = user_input.get(f"entity_{len(self.entities)} or leave blank to finish setup.", "")

            # Process the input
            if new_entity:
                # Validate the entered entity
                if new_entity in self.hass.states.async_entity_ids("sensor"):
                    self.entities.append(new_entity)  # Add to the list of valid entities
                else:
                    # Add an error for the current entity field
                    if len(self.entities) < 2:
                        errors[f"entity_{len(self.entities)}"] = "invalid_entity"
                    else:
                        errors[f"entity_{len(self.entities)} or leave blank to finish setup."] = "invalid_entity"
            else:
                # If the field is empty, finalize the configuration
                if self.entities:
                    # Check if an existing entry already exists
                    existing_entries = [
                        entry for entry in self.hass.config_entries.async_entries(DOMAIN)
                    ]
                    if existing_entries:
                        entry = existing_entries[0]

                        # Create a new data dictionary with updated entities
                        updated_entities = list(set(entry.data["entities"] + self.entities))
                        new_data = {**entry.data, "entities": updated_entities}

                        # Use `async_update_entry` to update the config entry
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

                # Show an error if no entities have been added
                if len(self.entities) < 2:
                    errors[f"entity_{len(self.entities)}"] = "no_entities"
                else:
                    errors[f"entity_{len(self.entities)} or leave blank to finish setup."] = "no_entities"

        # Build the form schema dynamically
        schema = self._build_schema()

        # Show the form with errors (if any)
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _build_schema(self):
        """Build the schema dynamically based on the entities entered so far."""
        schema = {}

        # Add previously entered entities as non-editable fields
        for i, entity in enumerate(self.entities):
            schema[vol.Optional(f"entity_{i}", default=entity)] = str

        # Add a new field for the next entity
        if len(self.entities) < 2:
            schema[vol.Optional(f"entity_{len(self.entities)}")] = str
        else:
            schema[vol.Optional(f"entity_{len(self.entities)} or leave blank to finish setup.")] = str

        return vol.Schema(schema)
