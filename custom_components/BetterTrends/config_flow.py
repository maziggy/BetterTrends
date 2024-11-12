import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.entity_registry import async_entries_for_config_entry
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BetterTrends."""
    VERSION = 1

    def __init__(self):
        self.sensors = []

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step to collect the first sensor."""
        if user_input is not None:
            sensor_id = user_input["sensor_0"].strip()

            # Check if the sensor is valid
            if not await self._validate_sensor(sensor_id):
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._build_initial_schema(),
                    errors={"sensor_0": "invalid_sensor"}
                )

            # Save the sensor if valid
            if sensor_id not in self.sensors:
                self.sensors.append(sensor_id)

            # Move to the next step to add more sensors or finish
            return await self.async_step_add_more()

        # Show the form to enter the first sensor
        return self.async_show_form(step_id="user", data_schema=self._build_initial_schema())

    async def async_step_add_more(self, user_input=None):
        """Allow the user to add more sensors or finish setup."""
        if user_input is not None:
            # Check if the user is adding a new sensor
            new_sensor = user_input.get("sensor_next", "").strip()
            if new_sensor:
                # Validate the sensor
                if not await self._validate_sensor(new_sensor):
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._build_additional_schema(),
                        errors={"sensor_next": "invalid_sensor"}
                    )

                # Check for duplicates
                if new_sensor in self.sensors:
                    return self.async_show_form(
                        step_id="add_more",
                        data_schema=self._build_additional_schema(),
                        errors={"sensor_next": "duplicate_sensor"}
                    )

                # Add the valid new sensor
                self.sensors.append(new_sensor)

            # Finish setup if 'finish' is checked
            if user_input.get("finish", False):
                return self.async_create_entry(title="Better Trends", data={"sensors": self.sensors})

        # Show the form to add another sensor or finish
        return self.async_show_form(step_id="add_more", data_schema=self._build_additional_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)

    def _build_initial_schema(self):
        """Builds the schema for the initial sensor input."""
        return vol.Schema({
            vol.Required("sensor_0", default=""): str  # Field to enter the first sensor
        })

    def _build_additional_schema(self):
        """Builds the schema for adding more sensors."""
        return vol.Schema({
            vol.Optional("sensor_next", default=""): str,  # Optional field to add a new sensor
            vol.Optional("finish", default=False): bool  # Checkbox to finish adding sensors
        })

    async def _validate_sensor(self, sensor_id):
        """Validates that a sensor exists and is valid."""
        # Perform validation by checking if the sensor_id is registered in Home Assistant
        if not sensor_id.startswith("sensor."):
            return False

        entity_registry = await self.hass.helpers.entity_registry.async_get(self.hass)
        return entity_registry.async_is_registered(sensor_id)
    

class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow to modify sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors after setup."""
        if user_input is not None:
            # Collect the sensors from the options form
            sensors = [sensor.strip() for sensor in user_input.values() if sensor]
            unique_sensors = list(dict.fromkeys(sensors))  # Remove duplicates

            # Update the config entry with the unique list of sensors
            self.hass.config_entries.async_update_entry(self.config_entry, options={"sensors": unique_sensors})

            # Reload the entry to apply changes immediately
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        # Show the form initially to configure sensors
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema()
        )

    def _build_options_schema(self):
        """Build schema dynamically for editing sensors."""
        sensors = self.config_entry.options.get("sensors", [])

        # Create schema for each sensor and add an extra field for adding a new sensor
        schema = {vol.Optional(f"sensor_{i}", default=sensor): str for i, sensor in enumerate(sensors)}
        schema[vol.Optional(f"sensor_{len(sensors)}", default="")] = str  # Field to add a new sensor

        return vol.Schema(schema)
