from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TartiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TartiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScaleOccupiedBinarySensor(coordinator)])


class ScaleOccupiedBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Dolu"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(self, coordinator: TartiCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.scale_mac}_occupied"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.scale_mac)},
            name="Tartı",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", self.coordinator.scale_mac)},
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_binary, self.async_write_ha_state
            )
        )

    @property
    def is_on(self) -> bool:
        return self.coordinator._occupied