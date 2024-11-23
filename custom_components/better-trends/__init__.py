import asyncio
from .utils import init_metrics, get_ha_data, set_ha_counter

async def async_setup_entry(hass, entry, async_add_entities):
    """Start background tasks."""
    config = entry.data
    api_url = config["api_url"]
    token = config["token"]
    interval = await get_ha_data(hass, api_url, token, "input_number.growbox_trend_interval")
    trend_values = await get_ha_data(hass, api_url, token, "input_number.growbox_trend_values")
    entities = config.get("entities", [])

    metrics = init_metrics(entities)

    async def update_metrics():
        while True:
            for metric in metrics:
                last = await get_ha_data(hass, api_url, token, metric["entity"])
                metric[f"value{len(metrics)}"] = last
                # Calculate trend, update metrics here as needed
            await asyncio.sleep(interval)

    hass.loop.create_task(update_metrics())
    return True
