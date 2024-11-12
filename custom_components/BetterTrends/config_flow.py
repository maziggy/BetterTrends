import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.sensors = []  # Store sensors during the initial flow

    async def async_step_user(self, user_input=None):
        """Initial setup step to gather the first sensor."""
        if user_input is not None:
            sensor_id = user_input["sensor"]

            if not self._is_valid_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._sensor_schema(),
                    errors={"sensor": "invalid_sensor"},
                    description_placeholders={"sensor_help": "Enter a valid sensor entity ID, e.g., sensor.temperature"}
                )

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

                if not self._is_valid_sensor(sensor_id):
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._sensor_schema(optional=True),
                        errors={"sensor": "invalid_sensor"},
                        description_placeholders={"sensor_help": "Enter an additional sensor ID or leave blank to finish."}
                    )

                self.sensors.append(sensor_id)
            else:
                return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        return self.async_show_form(
            step_id="add_more",
            data_schema=self._sensor_schema(optional=True),
            description_placeholders={"sensor_help": "Enter an additional sensor ID or leave blank to finish."}
        )

    def _sensor_schema(self, optional=False):
        return vol.Schema({
            vol.Optional("sensor") if optional else vol.Required("sensor"): str
        })

    def _is_valid_sensor(self, sensor_id):
        return self.hass.states.get(sensor_id) is not None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to allow modifying the sensor list after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors."""
        if user_input is not None:
            # Update the sensors list in the config entry with new sensors
            sensors = [sensor.strip() for sensor in user_input.values() if sensor.strip()]
            self.hass.config_entries.async_update_entry(self.config_entry, data={"sensors": sensors})
            return self.async_create_entry(title="", data={"sensors": sensors})

        # Prepopulate form with current sensors in options
        data_schema = self._build_options_schema(self.config_entry.data.get("sensors", []))
        return self.async_show_form(step_id="init", data_schema=data_schema)

    def _build_options_schema(self, sensors):
        """Dynamically build schema based on current sensors."""
        schema = {}
        for i, sensor in enumerate(sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str
        # Add an empty field for a new sensor
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str
        return vol.Schema(schema)
