class BetterTrendsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for modifying the list of sensors after setup."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        self.sensors = config_entry.data.get("sensors", [])

    async def async_step_init(self, user_input=None):
        """Manage options to add, remove, or edit sensors."""
        # If user_input is provided, update the sensors list
        if user_input is not None:
            # Collect sensors from individual fields into a list
            self.sensors = [sensor.strip() for key, sensor in user_input.items() if sensor.strip()]
            return self.async_create_entry(title="", data={"sensors": self.sensors})

        # If no user_input, show form for editing sensors
        schema = self._options_schema()
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={"sensor_help": "Enter a unique sensor ID per field."}
        )

    def _options_schema(self):
        """Dynamically generate schema based on current sensors list."""
        schema = {}

        # Add a field for each sensor
        for i, sensor in enumerate(self.sensors):
            schema[vol.Optional(f"sensor_{i}", default=sensor)] = str

        # Add an empty field to allow the user to add a new sensor
        schema[vol.Optional(f"sensor_{len(self.sensors)}", default="")] = str

        return vol.Schema(schema)

    def _is_valid_sensor(self, sensor_id):
        """Check if a sensor entity exists."""
        return self.hass.states.get(sensor_id) is not None
