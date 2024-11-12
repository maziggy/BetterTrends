from homeassistant.core import HomeAssistant
from .const import SENSOR_SUFFIX

def calculate_trends(hass: HomeAssistant, sensor_id: str):
    state = hass.states.get(sensor_id)
    if not state:
        return None

    trend_value = float(state.state)
    return {"trend_value": trend_value}
    