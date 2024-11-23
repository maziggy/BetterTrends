import logging
from homeassistant_api import Client, State

_LOGGER = logging.getLogger(__name__)

def init_metrics(entities):
    """Initialize metrics with entities and their default values."""
    metrics = []
    for entity in entities:
        metrics.append(
            {'entity': entity, **{f'value{i}': 0.0 for i in range(6)}}
        )

    _LOGGER.debug(f"init_metrics > metrics: {metrics}")
    return metrics


def calculate(entity, last, trend_values):
    """Calculate a value based on trend data."""
    value = 0
    counter = 1

    for key, val in entity.items():
        if "value" in key and counter <= trend_values:
            value += val
            counter += 1

    result = round(last - (value / trend_values), 1)
    _LOGGER.debug(f"calculate > entity: {entity}, last: {last}, values: {trend_values}, result: {result}")
    return result


async def set_ha_data(hass, api_url, token, entity, data):
    """Set data for a Home Assistant entity."""
    try:
        if data == -0.0:
            data = 0.0
        _LOGGER.debug(f"set_ha_data > entity: {entity}, data: {data}")
        with Client(api_url, token) as client:
            client.set_state(State(state=str(data), entity_id=entity + "_last"))
    except Exception as e:
        _LOGGER.error(f"set_ha_data > Error: {e}")


async def set_ha_counter(hass, api_url, token, entity, value):
    """Set a counter in Home Assistant."""
    try:
        _LOGGER.debug(f"set_ha_counter > entity: {entity}, value: {value}")
        with Client(api_url, token) as client:
            client.set_state(State(state=str(value), entity_id=entity))
    except Exception as e:
        _LOGGER.error(f"set_ha_counter > Error: {e}")


async def get_ha_data(hass, api_url, token, entity):
    """Get data from Home Assistant."""
    try:
        with Client(api_url, token) as client:
            state = client.get_state(entity_id=entity)
            result = round(float(state.state), 1)
            _LOGGER.debug(f"get_ha_data > entity: {entity}, result: {result}")
            return result
    except Exception as e:
        _LOGGER.error(f"get_ha_data > Error: {e}")
        return None
