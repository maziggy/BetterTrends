from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Better Trends integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Better Trends from a config entry."""
    # Store the configuration data for the integration
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the setup to the sensor platform and await it
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle unloading of a config entry."""
    # Remove entry data from hass.data
    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Unload the sensor platform
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    return True
