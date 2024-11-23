"""BetterTrends custom integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "better_trends"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BetterTrends from a config entry."""
    _LOGGER.debug(f"Setting up BetterTrends for entry: {entry.entry_id}")

    # Forward the setup to the appropriate platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])

    _LOGGER.debug(f"Forwarded entry setup for sensor and number platforms")
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_ok &= await hass.config_entries.async_forward_entry_unload(entry, "number")

    if unload_ok:
        # Safely remove entry from hass.data
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok
