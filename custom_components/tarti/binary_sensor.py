from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TartiCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    c: TartiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScaleOccupied(c)])


class ScaleOccupied(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Dolu"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, c: TartiCoordinator):
        self.coordinator = c
        self._attr_unique_id = f"{c.entry.entry_id}_occupied"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Tartı",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", self.coordinator.scale_address)},
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_binary, self.async_write_ha_state
            )
        )

    @property
    def is_on(self):
        return self.coordinator._occupied