from homeassistant.components.persistent_notification import async_create
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import aiohttp_client
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from aiohttp import web
from pathlib import Path
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "better_trends"

LOVELACE_RESOURCES = [
    {"url": "/better_trends/trend-card.min.js", "type": "module"},
    {"url": "/better_trends/trend-card-lite.min.js", "type": "module"},
]


async def _register_lovelace_resources(hass: HomeAssistant):
    """Register the Lovelace resources."""
    session = aiohttp_client.async_get_clientsession(hass)
    base_url = hass.config.external_url or hass.config.internal_url

    if not base_url:
        _LOGGER.error("Home Assistant external or internal URL is not configured.")
        raise RuntimeError("Cannot register Lovelace resources without a base URL.")

    for resource in LOVELACE_RESOURCES:
        url = resource["url"]
        full_url = f"{base_url}{url}"

        # Check if the resource is already available
        try:
            async with session.get(full_url) as resp:
                if resp.status == 200:
                    _LOGGER.info(f"Lovelace resource already exists: {full_url}")
                    continue
        except Exception as err:
            _LOGGER.warning(f"Could not verify resource {full_url}: {err}")

        # Add the resource if not found
        try:
            await hass.services.async_call(
                "lovelace",
                "resources/create",
                {"res_type": resource["type"], "url": url},
            )
            _LOGGER.info(f"Added Lovelace resource: {url}")
        except Exception as err:
            _LOGGER.error(f"Failed to add Lovelace resource {url}: {err}")
            raise RuntimeError(f"Failed to add resource: {url}") from err


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
    component_path = Path(hass.config.path("custom_components")) / DOMAIN

    # Register the resource view to serve files
    hass.http.register_view(BetterTrendsResourceView(str(component_path)))

    # Add the Lovelace resources automatically
    try:
        await _register_lovelace_resources(hass)
    except RuntimeError as err:
        _LOGGER.error(f"Error registering Lovelace resources: {err}")
        message = (
            f"BetterTrends was installed, but the Lovelace resources could not be added automatically.\n\n"
            f"Please add them manually via Dashboard Resources:\n\n"
            f"- URL: {LOVELACE_RESOURCES[0]['url']} (Type: {LOVELACE_RESOURCES[0]['type']})\n"
            f"- URL: {LOVELACE_RESOURCES[1]['url']} (Type: {LOVELACE_RESOURCES[1]['type']})\n\n"
            "Go to **Settings > Dashboards > Resources** to add them."
        )
        async_create(hass, message, title="BetterTrends Setup")

    # Forward the setup to the appropriate platforms
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