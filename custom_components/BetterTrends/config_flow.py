import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Initial setup step to gather the first sensor or redirect to options if already configured."""
        # Check if there's already an entry for this integration
        if self._entry_exists():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            sensor_id = user_input["sensor"]

            # Validate sensor ID
            if not self._is_valid_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._sensor_schema(),
                    errors={"sensor": "invalid_sensor"},
                    description_placeholders={"sensor_help": "Enter a valid sensor entity ID, e.g., sensor.temperature"}
                )
            
            # Check for duplicate sensor in initial setup
            if sensor_id in self.sensors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._sensor_schema(),
                    errors={"sensor": "duplicate_sensor"},
                    description_placeholders={"sensor_help": "This sensor has already been added."}
                )

            # Add the sensor if it's valid and not a duplicate
            self.sensors.append(sensor_id)
            return await self.async_step_add_more()

        return self.async_show_form(
            step_id="user",
            data_schema=self._sensor_schema(),
            description_placeholders={"sensor_help": "Enter a valid sensor entity ID, e.g., sensor.temperature"}
        )

    async def async_step_add_more(self, user_input=None):
        """Step to add more sensors or finish setup."""
        if user_input is not None:
            if "sensor" in user_input and user_input["sensor"]:
                sensor_id = user_input["sensor"]

                # Validate sensor ID
                if not self._is_valid_sensor(sensor_id):
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._sensor_schema(optional=True),
                        errors={"sensor": "invalid_sensor"},
                        description_placeholders={"sensor_help": "Enter an additional sensor ID or leave blank to finish."}
                    )

                # Check for duplicate sensor in setup addition
                if sensor_id in self.sensors:
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._sensor_schema(optional=True),
                        errors={"sensor": "duplicate_sensor"},
                        description_placeholders={"sensor_help": "This sensor has already been added."}
                    )

                # Add the new sensor to the list
                self.sensors.append(sensor_id)
            else:
                # Finalize setup and save all sensors in the config entry
                _LOGGER.debug(f"Creating config entry with sensors: {self.sensors}")
                return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        # Show form for adding additional sensors
        return self.async_show_form(
            step_id="add_more",
            data_schema=self._sensor_schema(optional=True),
            description_placeholders={"sensor_help": "Enter an additional sensor ID or leave blank to finish."}
        )

    def _sensor_schema(self, optional=False):
        """Return the schema for a single sensor input field."""
        return vol.Schema({
            vol.Optional("sensor") if optional else vol.Required("sensor"): str
        })

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists in Home Assistant."""
        entity = self.hass.states.get(sensor_id)
        # Ensure the entity exists and is of domain 'sensor'
        return entity is not None and entity.domain == "sensor"

    def _entry_exists(self):
        """Check if an entry with the same domain already exists."""
        existing_entries = self._async_current_entries()
        return any(entry.domain == DOMAIN for entry in existing_entries)

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

            # If there are validation errors, show the form again with error messages
            if errors:
                _LOGGER.debug(f"Validation errors in options flow: {errors}")
                # Redisplay the form with the existing inputs without adding a new row
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_options_schema(user_input.values()),
                    errors=errors
                )

            # Update `config_entry.data` with the new sensor list only if all are valid
            _LOGGER.debug(f"Updating data with sensors: {sensors}")
            new_data = {**self.config_entry.data, "sensors": sensors}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)

            # Force reload of the config entry to apply changes immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            # Use an empty dictionary for `data` to avoid TypeError
            return self.async_create_entry(title="", data={})

        # Retrieve the current list of sensors from data
        current_sensors = self.config_entry.data.get("sensors", [])
        
        # Log the retrieved current sensors list
        _LOGGER.debug(f"Current sensors for options form: {current_sensors}")

        # Update the schema with the current sensors list so that it always shows the latest state
        data_schema = self._build_options_schema(current_sensors)
        
        return self.async_show_form(step_id="init", data_schema=data_schema)

    def _build_options_schema(self, sensors):
        """Dynamically build schema based on current sensors."""
        schema = {}
        for i, sensor in enumerate(sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field for adding a new sensor
        return vol.Schema(schema)

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists in Home Assistant."""
        entity = self.hass.states.get(sensor_id)
        # Ensure the entity exists and is of domain 'sensor'
        return entity is not None and entity.domain == "sensor"
