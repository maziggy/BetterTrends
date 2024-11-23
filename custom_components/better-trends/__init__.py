from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BetterTrends from a config entry."""
    _LOGGER.debug("Setting up BetterTrends entry")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Forward entry setup for sensor and number domains
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    _LOGGER.debug("Forwarded entry setup for sensor platform")
    await hass.config_entries.async_forward_entry_setup(entry, "number")
    _LOGGER.debug("Forwarded entry setup for number platform")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a BetterTrends config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "number"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
