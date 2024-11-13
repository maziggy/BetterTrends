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
    """Options flow to modify sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors."""
        _LOGGER.debug("Entering async_step_init with user_input: %s", user_input)
        
        if user_input is not None:
            # Collect updated sensors from the options form and validate each
            sensors = []
            errors = {}

            # Validate each entered sensor and check for duplicates
            seen_sensors = set()
            for key, sensor_id in user_input.items():
                sensor_id = sensor_id.strip()
                if sensor_id:
                    if sensor_id in seen_sensors:
                        errors[key] = "duplicate_sensor"  # Flag duplicate sensor entry
                    elif not self._is_valid_sensor(sensor_id):
                        errors[key] = "invalid_sensor"  # Flag invalid sensor
                    else:
                        sensors.append(sensor_id)
                        seen_sensors.add(sensor_id)

            # Log validation results
            _LOGGER.debug("Validation complete. Sensors: %s, Errors: %s", sensors, errors)

            # If there are validation errors, show the form again with error messages
            if errors:
                _LOGGER.debug("Displaying form again due to errors: %s", errors)
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_options_schema(user_input.values(), add_new_row=False),
                    errors=errors
                )

            # Update the list of sensors in the config entry only if no errors
            _LOGGER.debug("Updating config entry data with sensors: %s", sensors)
            new_data = {**self.config_entry.data, "sensors": sensors}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            # Determine if the setup should finish based on the last field
            last_field_key = f"sensor_{len(sensors)}"
            if last_field_key in user_input and not user_input[last_field_key].strip():
                # If the last field is blank, complete the setup
                _LOGGER.debug("Last field is blank, finishing setup.")
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

            # If the last field was not blank, show the form again for additional entries
            _LOGGER.debug("Last field is not blank, showing form again to allow more sensors.")
            return self.async_show_form(
                step_id="init",
                data_schema=self._build_options_schema(sensors, add_new_row=True)
            )

        # Retrieve the current list of sensors from data
        current_sensors = self.config_entry.data.get("sensors", [])
        
        # Log the retrieved current sensors list
        _LOGGER.debug("Displaying initial form with current sensors: %s", current_sensors)

        # Show form initially with a new row added
        data_schema = self._build_options_schema(current_sensors, add_new_row=True)
        
        return self.async_show_form(step_id="init", data_schema=data_schema)

    def _build_options_schema(self, sensors, add_new_row=True):
        """Dynamically build schema based on current sensors."""
        schema = {}
        for i, sensor in enumerate(sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str
        # Only add a new row if add_new_row is True
        if add_new_row:
            schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field for adding a new sensor
        _LOGGER.debug("Building options schema with add_new_row=%s: %s", add_new_row, schema)
        return vol.Schema(schema)

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists in Home Assistant."""
        entity = self.hass.states.get(sensor_id)
        # Ensure the entity exists and is of domain 'sensor'
        valid = entity is not None and entity.domain == "sensor"
        _LOGGER.debug("Validating sensor '%s': %s", sensor_id, valid)
        return valid
