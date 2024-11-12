import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from .calculation import calculate_trends  # Assuming you have a calculation function in calculation.py
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up BetterTrends integration."""
    # This function might be empty, but it's required for Home Assistant to recognize the integration
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BetterTrends from a config entry."""

    # Define default values for the sensors
    interval_seconds = 300  # Set interval to 300 seconds (5 minutes)
    steps = 10  # Default for better_trends_steps
    steps_curr = 0  # Initial value for the current step

    # Initialize the sensors with their default values
    hass.states.async_set("sensor.better_trends_interval", interval_seconds, {"unit_of_measurement": "seconds"})
    hass.states.async_set("sensor.better_trends_steps", steps, {"unit_of_measurement": "number"})
    hass.states.async_set("sensor.better_trends_steps_curr", steps_curr, {"unit_of_measurement": "number"})

    # Background task to update the trend sensors at the specified interval
    interval = timedelta(seconds=interval_seconds)
    
    async def update_sensors(_):
        """Perform trend calculations and update steps_curr."""
        nonlocal steps_curr

        # Perform trend calculations and update the corresponding sensors
        await calculate_trends(hass, entry)

        # Update steps_curr and reset it if it reaches the maximum number of steps
        steps_curr = (steps_curr + 1) % steps
        hass.states.async_set("sensor.better_trends_steps_curr", steps_curr, {"unit_of_measurement": "number"})

        _LOGGER.debug("Updated sensor.better_trends_steps_curr to %s", steps_curr)

    # Track time and call `update_sensors` every `interval` seconds
    async_track_time_interval(hass, update_sensors, interval)

    return True
