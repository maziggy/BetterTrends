import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class BetterTrendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            sensors = user_input.get("sensors")

            if not sensors:
                errors["sensors"] = "Please provide comma separated list of sensors."
            else:
                return self.async_create_entry(title="Better Trends", data=user_input)

        data_schema = vol.Schema({
            vol.Required("sensors", description={"suggested_value": "sensor.one, sensor.two, sensor.three, ..."}): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "sensors": "Comma separated list of sensors"
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BetterTrendsOptionsFlowHandler(config_entry)


class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("sensors", default=self.config_entry.data.get("sensors")): str
            })
        )
