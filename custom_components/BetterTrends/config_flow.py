import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.sensors = []  # Store all sensors here during the flow

    async def async_step_user(self, user_input=None):
        """Initial step for adding the first sensor."""
        if user_input is not None:
            sensor_id = user_input["sensor"]

            # Validate and add the sensor
            if not self._is_valid_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._sensor_schema(),
                    errors={"sensor": "invalid_sensor"},
                    description_placeholders={"sensor_help": "Enter a valid sensor entity ID, e.g., sensor.temperature"}
                )

            # Add the first sensor to the list and proceed to the next step
            self.sensors.append(sensor_id)
            return await self.async_step_add_more()

        # Show the initial form with help text
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

                # Validate the new sensor and add it
                if not self._is_valid_sensor(sensor_id):
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._sensor_schema(optional=True),
                        errors={"sensor": "invalid_sensor"},
                        description_placeholders={"sensor_help": "Enter an additional sensor ID or leave blank to finish."}
                    )

                # Add the new sensor to the list
                self.sensors.append(sensor_id)
                # Repeat this step to allow adding more sensors

            else:
                # User opted to finish, create the config entry
                return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        # Show the form for adding more sensors
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
        return self.hass.states.get(sensor_id) is not None
