from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfMass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import TartiCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    c: TartiCoordinator = hass.data[DOMAIN][entry.entry_id]
    ents = [PersonWeightSensor(c, n) for n in c.persons]
    ents.append(PendingWeightSensor(c))
    async_add_entities(ents)


class _Base(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, c: TartiCoordinator):
        self.coordinator = c

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name="Tartı",
            manufacturer=MANUFACTURER,
            model=MODEL,
            connections={("bluetooth", self.coordinator.scale_address)},
        )


class PersonWeightSensor(_Base):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, c, person):
        super().__init__(c)
        self.person = person
        self._attr_name = person
        self._attr_unique_id = f"{c.entry.entry_id}_{person}_weight"

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self.coordinator.signal_person, self._on_update
            )
        )

    @callback
    def _on_update(self, person):
        if person == self.person:
            self.async_write_ha_state()

    @property
    def native_value(self):
        return self.coordinator.persons[self.person].last_weight


class PendingWeightSensor(_Base):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_name = "Bekleyen ölçüm"

    def __init__(self, c):
        super().__init__(c)
        self._attr_unique_id = f"{c.entry.entry_id}_pending"

    async def async_added_to_hass(self):
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