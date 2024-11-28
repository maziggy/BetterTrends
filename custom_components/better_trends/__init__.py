from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import logging
from pathlib import Path
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

_LOGGER = logging.getLogger(__name__)

DOMAIN = "better_trends"

# Define Lovelace resources
LOVELACE_RESOURCES = [
    {"url": "/hacsfiles/better_trends/lovelace/trend-card.min.js", "type": "module"},
    {"url": "/hacsfiles/better_trends/lovelace/trend-card-lite.min.js", "type": "module"},
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BetterTrends from a config entry."""
    component_path = Path(__file__).parent
    hass.http.register_view(BetterTrendsResourceView(component_path))

    # Check if the notification was already sent
    notified = entry.data.get("notified", False)

    if not notified:
        # Send the notification
        async_create(
            hass,
            (
                "BetterTrends was installed, but the Lovelace resources could not be added automatically.\n\n"
                f"Please add them manually via Dashboard Resources:\n\n"
                f"- URL: {LOVELACE_RESOURCES[0]['url']} (Type: {LOVELACE_RESOURCES[0]['type']})\n"
                f"- URL: {LOVELACE_RESOURCES[1]['url']} (Type: {LOVELACE_RESOURCES[1]['type']})\n\n"
                "Go to **Settings > Dashboards > Resources** to add them."
            ),
            title="BetterTrends Installation",
            notification_id="better_trends_install",
        )

        # Update the config entry to mark the notification as sent
        new_data = {**entry.data, "notified": True}
        hass.config_entries.async_update_entry(entry, data=new_data)
        _LOGGER.debug("BetterTrends notification sent and entry updated.")

    # Forward the setup to the appropriate platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "number"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    unload_ok &= await hass.config_entries.async_forward_entry_unload(entry, "number")

    if unload_ok:
        # Clean up hass.data for the integration
        if DOMAIN in hass.data:
            hass.data.pop(DOMAIN, None)

    return unload_ok


class BetterTrendsResourceView(HomeAssistantView):
    """Serve custom Lovelace resources for BetterTrends."""

    url = "/hacsfiles/better_trends/lovelace/{filename}"
    name = "hacsfiles:better_trends"
    requires_auth = False

    def __init__(self, component_path):
        self._component_path = Path(component_path)

    async def get(self, request, filename):
        """Serve the requested file."""
        file_path = self._component_path / "lovelace" / filename
        if not file_path.exists():
            return web.Response(status=404, text="Resource not found.")
        return web.FileResponse(file_path)