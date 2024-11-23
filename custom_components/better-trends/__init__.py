from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BetterTrends from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry

    # Forward entry setup for sensor and number domains
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    await hass.config_entries.async_forward_entry_setup(entry, "number")

    return True
            
                
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a BetterTrends config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor", "number"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
    

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload BetterTrends entry when new entities are added."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
