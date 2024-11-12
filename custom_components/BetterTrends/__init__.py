import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .calculation import calculate_trends
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry):
    """Set up BetterTrends from a config entry."""
    
    # Initialize the three sensors with default values
    interval_seconds = entry.options.get("update_interval", 5) * 60  # Convert minutes to seconds
    steps = 10  # Default for better_trends_steps (adjust as needed)
    steps_curr = 0  # Initial value for the current step

    # Set the initial values of the sensors
    hass.states.async_set("sensor.better_trends_interval", interval_seconds, {"unit_of_measurement": "seconds"})
    hass.states.async_set("sensor.better_trends_steps", steps, {"unit_of_measurement": "number"})
    hass.states.async_set("sensor.better_trends_steps_curr", steps_curr, {"unit_of_measurement": "number"})

    # Background task to update the trend sensors
    interval = timedelta(seconds=interval_seconds)
    
    async def update_sensors(_):
        """Update sensors with trend calculations and track steps."""
        nonlocal steps_curr

        # Perform calculations and update trend sensors
        await calculate_trends(hass, entry)

        # Update steps_curr and reset if it reaches steps
        steps_curr = (steps_curr + 1) % steps
        hass.states.async_set("sensor.better_trends_steps_curr", steps_curr, {"unit_of_measurement": "number"})

        _LOGGER.debug("Updated sensor.better_trends_steps_curr to %s", steps_curr)

    # Track time and call `update_sensors` every interval
    async_track_time_interval(hass, update_sensors, interval)

    return True
