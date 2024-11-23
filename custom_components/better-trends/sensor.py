class EditableIntervalSensor(SensorEntity):
    """A sensor representing the editable interval."""

    def __init__(self, hass, entry):
        self._state = DEFAULT_INTERVAL  # Default value
        self.hass = hass
        self._entry = entry
        self._input_number_entity = "input_number.trend_sensor_interval"
        self._attr_name = "Trend Sensor Interval"
        self._attr_unique_id = "trend_sensor_interval"

    @property
    def native_value(self):
        """Return the current interval value."""
        return self._state

    async def async_added_to_hass(self):
        """Initialize the sensor and listen for changes to the input_number."""
        _LOGGER.info("Initializing Trend Sensor Interval with input_number support.")

        # Create the input_number entity dynamically if it doesn't exist
        await self._ensure_input_number_exists(
            self._input_number_entity,
            name="Trend Sensor Interval",
            min_value=1,
            max_value=3600,
            initial_value=DEFAULT_INTERVAL,
        )

        # Listen for changes to the input_number entity
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

        # Initialize the state from the input_number
        self._update_state_from_input_number()

    async def _ensure_input_number_exists(self, entity_id, name, min_value, max_value, initial_value):
        """Ensure the input_number exists in Home Assistant."""
        if not self.hass.states.get(entity_id):
            await self.hass.services.async_call(
                "input_number",
                "create",
                {
                    "entity_id": entity_id,
                    "name": name,
                    "min": min_value,
                    "max": max_value,
                    "step": 1,
                    "initial": initial_value,
                },
            )
            _LOGGER.info(f"Created input_number entity: {entity_id}")

    @callback
    def _handle_state_change(self, event):
        """Handle changes to the input_number."""
        if event.data.get("entity_id") == self._input_number_entity:
            self._update_state_from_input_number()

    def _update_state_from_input_number(self):
        """Update the sensor state based on the input_number value."""
        state = self.hass.states.get(self._input_number_entity)
        if state:
            try:
                self._state = int(float(state.state))
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning(f"Invalid value for {self._input_number_entity}: {state.state}")


class EditableStepsSensor(SensorEntity):
    """A sensor representing the editable steps."""

    def __init__(self, hass, entry):
        self._state = DEFAULT_TREND_VALUES  # Default value
        self.hass = hass
        self._entry = entry
        self._input_number_entity = "input_number.trend_sensor_steps"
        self._attr_name = "Trend Sensor Steps"
        self._attr_unique_id = "trend_sensor_steps"

    @property
    def native_value(self):
        """Return the current steps value."""
        return self._state

    async def async_added_to_hass(self):
        """Initialize the sensor and listen for changes to the input_number."""
        _LOGGER.info("Initializing Trend Sensor Steps with input_number support.")

        # Create the input_number entity dynamically if it doesn't exist
        await self._ensure_input_number_exists(
            self._input_number_entity,
            name="Trend Sensor Steps",
            min_value=1,
            max_value=100,
            initial_value=DEFAULT_TREND_VALUES,
        )

        # Listen for changes to the input_number entity
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._handle_state_change)

        # Initialize the state from the input_number
        self._update_state_from_input_number()

    async def _ensure_input_number_exists(self, entity_id, name, min_value, max_value, initial_value):
        """Ensure the input_number exists in Home Assistant."""
        if not self.hass.states.get(entity_id):
            await self.hass.services.async_call(
                "input_number",
                "create",
                {
                    "entity_id": entity_id,
                    "name": name,
                    "min": min_value,
                    "max": max_value,
                    "step": 1,
                    "initial": initial_value,
                },
            )
            _LOGGER.info(f"Created input_number entity: {entity_id}")

    @callback
    def _handle_state_change(self, event):
        """Handle changes to the input_number."""
        if event.data.get("entity_id") == self._input_number_entity:
            self._update_state_from_input_number()

    def _update_state_from_input_number(self):
        """Update the sensor state based on the input_number value."""
        state = self.hass.states.get(self._input_number_entity)
        if state:
            try:
                self._state = int(float(state.state))
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning(f"Invalid value for {self._input_number_entity}: {state.state}")
