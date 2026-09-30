from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant, callback
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
    entities: list[SensorEntity] = [
        PersonWeightSensor(coordinator, name) for name in coordinator.persons
    ]
    entities.append(PendingWeightSensor(coordinator))
    async_add_entities(entities)


class _BaseScaleEntity(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: TartiCoordinator) -> None:
        self.coordinator = coordinator

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.scale_mac)},
            name="Tartı",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", self.coordinator.scale_mac)},
        )


class PersonWeightSensor(_BaseScaleEntity):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: TartiCoordinator, person: str) -> None:
        super().__init__(coordinator)
        self.person = person
        self._attr_name = person
        self._attr_unique_id = f"{coordinator.scale_mac}_{person}_weight"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_person, self._on_update
            )
        )

    @callback
    def _on_update(self, person: str) -> None:
        if person == self.person:
            self.async_write_ha_state()

    @property
    def native_value(self):
        return self.coordinator.persons[self.person].last_weight


class PendingWeightSensor(_BaseScaleEntity):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_name = "Bekleyen ölçüm"

    def __init__(self, coordinator: TartiCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.scale_mac}_pending"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_pending, self.async_write_ha_state
            )
        )

    @property
    def native_value(self):
        return self.coordinator._pending_weight

    @property
    def extra_state_attributes(self):
        return {"candidates": self.coordinator._pending_candidates}