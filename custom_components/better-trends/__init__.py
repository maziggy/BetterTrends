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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading BetterTrends entry: {entry.entry_id}")

    # Unload the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "number"])

    if unload_ok:
        _LOGGER.debug(f"Successfully unloaded BetterTrends platforms for entry: {entry.entry_id}")
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
