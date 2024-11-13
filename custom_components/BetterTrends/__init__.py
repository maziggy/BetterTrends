import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity import Entity

from .calculation import calculate_trends  # Assuming you have a calculation function in calculation.py
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up BetterTrends integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BetterTrends from a config entry."""

    # Get settings from ConfigEntry options or set defaults
    interval_seconds = entry.options.get("update_interval", 300)
    steps = entry.options.get("steps", 10)
    steps_curr = 0  # Initial value for the current step

    # Register sensors in Home Assistant’s state machine using async_add_entities
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

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
