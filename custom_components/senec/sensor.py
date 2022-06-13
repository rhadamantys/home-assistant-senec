"""Platform for Senec sensors."""
import logging

import homeassistant.helpers.config_validation as cv
from datetime import datetime
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from . import SenecDataUpdateCoordinator, SenecEntity
from .const import DOMAIN, SENEC_SENSOR_DERIVATIVE, SENEC_SENSOR_STANDARD, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities
):
    """Initialize sensor platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    for description in SENSOR_TYPES:
        if description.type == SENEC_SENSOR_STANDARD:
            entity = SenecSensor(coordinator, description)
        elif description.type == SENEC_SENSOR_DERIVATIVE:
            entity = SenecSensorDerivative(coordinator, description)
        entities.append(entity)

    async_add_entities(entities)


class SenecSensor(SenecEntity, SensorEntity):
    """Sensor for the single values (e.g. pv power, ac power)."""

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)

        title = self.coordinator._entry.title
        key = self.entity_description.key
        name = self.entity_description.name
        self.entity_id = f"sensor.{title}_{key}"
        self._attr_name = f"{title} {name}"


class SenecSensorDerivative(SenecSensor):
    """Sensor for the single derivative values
    (e.g. current power consumption based on total power consumed).
    """

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize a singular value sensor."""
        super().__init__(coordinator=coordinator, description=description)

        self._attr_last_changed = datetime.now().timestamp()
        self._attr_last_value = -1.0

    @property
    def state(self):
        """Return the current state."""
        sensor = self.entity_description.key
        now = datetime.now().timestamp()
        value = getattr(self.coordinator.senec, sensor)
        try:
            current_consumption = float(value)
        except ValueError:
            current_consumption = -1.0

        if (self._attr_last_value < 0.0) or (current_consumption < 0.0):
            value = getattr(self.coordinator.senec, "house_power")
            try:
                float_value = round(float(value), 2)
            except ValueError:
                float_value = value

        else:
            float_value = (
                (current_consumption - self._attr_last_value)
                * 1000.0
                * 3600.0
                / (now - self._attr_last_changed)
            )
            float_value = round(float_value, 2)

        if current_consumption > 0.0:
            self._attr_last_changed = now
            self._attr_last_value = current_consumption

        return float_value

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        sensor = self.entity_description.key
        return f"{self._name}_{sensor}_derivative"
