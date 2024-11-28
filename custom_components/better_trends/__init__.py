from homeassistant.components.http import HomeAssistantView
from homeassistant.loader import async_get_integration
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry
from homeassistant.helpers import aiohttp_client
from homeassistant.core import HomeAssistant
from pathlib import Path
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "better_trends"

LOVELACE_RESOURCES = [
    {"url": "/better_trends/trend-card.min.js", "type": "module"},
    {"url": "/better_trends/trend-card-lite.min.js", "type": "module"},
]

async def _register_lovelace_resources(hass):
    """Register custom Lovelace resources."""
    # Ensure the 'lovelace' integration is loaded
    lovelace_integration = await async_get_integration(hass, "lovelace")

    if not lovelace_integration:
        _LOGGER.error("Lovelace integration not found, unable to register resources.")
        return

    # Fetch the Lovelace resources storage
    url = "/api/resources"
    session = aiohttp_client.async_get_clientsession(hass)
    async with session.get(f"{hass.config.api.base_url}{url}") as resp:
        if resp.status != 200:
            _LOGGER.error("Failed to fetch Lovelace resources: %s", resp.status)
            return
        existing_resources = await resp.json()

    # Register any missing resources
    for resource in LOVELACE_RESOURCES:
        if not any(r["url"] == resource["url"] for r in existing_resources):
            async with session.post(f"{hass.config.api.base_url}{url}", json=resource) as resp:
                if resp.status != 200:
                    _LOGGER.error("Failed to register Lovelace resource: %s", resp.status)
                else:
                    _LOGGER.info("Registered Lovelace resource: %s", resource["url"])


class BetterTrendsResourceView(HomeAssistantView):
    """Serve custom Lovelace resources."""

    url = "/better_trends/{filename}"
    name = "better_trends:resources"
    requires_auth = False

    def __init__(self, component_path):
        self._component_path = Path(component_path)

    async def get(self, request, filename):
        """Serve the requested file."""
        file_path = self._component_path / "lovelace" / filename

        if not file_path.exists() or not file_path.is_file():
            return web.Response(status=404, text="Resource not found.")

        return web.FileResponse(file_path)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BetterTrends from a config entry."""
    # Serve Lovelace resources
    hass.http.register_view(BetterTrendsResourceView(hass.config.path("custom_components/better_trends")))

    # Register Lovelace resources
    await _register_lovelace_resources(hass)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_ok &= await hass.config_entries.async_forward_entry_unload(entry, "number")

    if unload_ok:
        # Safely remove entry from hass.data
        if DOMAIN in hass.data:
            hass.data[DOMAIN].pop(entry.entry_id, None)
            if not hass.data[DOMAIN]:  # If the domain is empty, remove it
                hass.data.pop(DOMAIN, None)

    return unload_ok
