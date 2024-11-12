import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Initial step to gather the first sensor."""
        if user_input is not None:
            sensor_id = user_input["sensor"]
            if not self._is_valid_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._sensor_schema(),
                    errors={"sensor": "invalid_sensor"},
                    description_placeholders={"sensor_help": "Enter a valid sensor entity, e.g. sensor.temperature"}
                )

            # Add the first sensor to the list and proceed to the next step
            self.sensors.append(sensor_id)
            return await self.async_step_add_sensors()

        # Show the initial form with help text
        return self.async_show_form(
            step_id="user",
            data_schema=self._sensor_schema(),
            description_placeholders={"sensor_help": "Enter a valid sensor entity, e.g. sensor.temperature"}
        )

    async def async_step_add_sensors(self, user_input=None):
        """Step to add more sensors or finish the setup."""
        if user_input is not None:
            if "sensor" in user_input and user_input["sensor"]:
                sensor_id = user_input["sensor"]

                # Validate the new sensor
                if not self._is_valid_sensor(sensor_id):
                    return self.async_show_form(
                        step_id="add_sensors",
                        data_schema=self._sensor_schema(optional=True),
                        errors={"sensor": "invalid_sensor"},
                        description_placeholders={"sensor_help": "Enter an additional sensor entity or leave blank to finish."}
                    )

                # Add the new sensor to the list
                self.sensors.append(sensor_id)

            # If the user leaves the field blank, finalize the setup
            return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        # Show the form for adding additional sensors
        return self.async_show_form(
            step_id="add_sensors",
            data_schema=self._sensor_schema(optional=True),
            description_placeholders={"sensor_help": "Enter an additional sensor entity or leave blank to finish."}
        )

    def _sensor_schema(self, optional=False):
        """Return the schema for a single sensor input field."""
        return vol.Schema({
            vol.Optional("sensor") if optional else vol.Required("sensor"): str
        })

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists in Home Assistant."""
        return self.hass.states.get(sensor_id) is not None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to allow modifying the sensor list after initial setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.sensors = config_entry.data.get("sensors", [])

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors."""
        if user_input is not None:
            # Update sensors list based on user input
            self.sensors = [sensor.strip() for sensor in user_input["sensors"] if sensor.strip()]
            return self.async_create_entry(title="", data={"sensors": self.sensors})

        # Show form for editing sensors with each sensor in its own field
        schema = self._options_schema()
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"sensor_help": "Enter one sensor entity per field."}
        )

    def _options_schema(self):
        """Create a dynamic schema based on the current list of sensors."""
        schema = {}
        for i, sensor in enumerate(self.sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str

        # Add an empty field to allow adding a new sensor
        schema[vol.Optional(f"sensor_{len(self.sensors)}", default="")] = str

        return vol.Schema(schema)

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists in Home Assistant."""
        return self.hass.states.get(sensor_id) is not None
