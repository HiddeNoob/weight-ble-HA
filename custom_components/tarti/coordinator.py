from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_PERSONS,
    CONF_PERSON_NAME,
    CONF_SCALE_MAC,
    DOMAIN,
    EVENT_PENDING,
    MIN_VALID_WEIGHT,
    STABILITY_READINGS,
    STABILITY_TOLERANCE,
)

_LOGGER = logging.getLogger(__name__)


def parse_scale(data: bytes):
    off = 2 if (len(data) >= 15 and data[0] == 0xC0) else 0
    if len(data) < off + 13:
        return None
    weight = int.from_bytes(data[off:off + 2], "big") / 100.0
    mac = data[off + 7: off + 13]
    return weight, mac


@dataclass
class PersonState:
    name: str
    last_weight: float | None = None


class TartiCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        cfg = {**entry.data, **entry.options}

        self.scale_mac = cfg[CONF_SCALE_MAC].upper()
        self.scale_mac_bytes = bytes.fromhex(self.scale_mac.replace(":", ""))

        self.persons: dict[str, PersonState] = {
            p[CONF_PERSON_NAME]: PersonState(name=p[CONF_PERSON_NAME])
            for p in cfg.get(CONF_PERSONS, [])
        }

        self._cancel = []
        self._weight_buffer: list[float] = []
        self._occupied = False
        self._session_person: str | None = None
        self._session_pending_fired = False
        self._pending_weight: float | None = None
        self._pending_candidates: list[str] = []

    @property
    def signal_person(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_person"

    @property
    def signal_binary(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_binary"

    @property
    def signal_pending(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_pending"

    async def async_start(self) -> None:
        self._cancel.append(
            async_register_callback(
                self.hass,
                self._on_scale_adv,
                BluetoothCallbackMatcher(address=self.scale_mac),
                BluetoothScanningMode.PASSIVE,
            )
        )
        _LOGGER.info("Tartı hazır: %s", self.scale_mac)

    async def async_stop(self) -> None:
        for c in self._cancel:
            c()
        self._cancel.clear()

    @callback
    def _on_scale_adv(self, info: BluetoothServiceInfoBleak, _change) -> None:
        for _mid, data in info.manufacturer_data.items():
            parsed = parse_scale(data)
            if not parsed:
                continue
            weight, mac = parsed
            if mac != self.scale_mac_bytes:
                continue
            self._handle_weight(weight)
            return

    def _is_stable(self) -> bool:
        if len(self._weight_buffer) < STABILITY_READINGS:
            return False
        recent = self._weight_buffer[-STABILITY_READINGS:]
        return (max(recent) - min(recent)) <= STABILITY_TOLERANCE

    def _set_occupied(self, occupied: bool) -> None:
        if occupied == self._occupied:
            return
        self._occupied = occupied
        async_dispatcher_send(self.hass, self.signal_binary)

    def _handle_weight(self, weight: float) -> None:
        if weight < MIN_VALID_WEIGHT:
            self._weight_buffer.clear()
            self._session_person = None
            self._session_pending_fired = False
            self._pending_weight = None
            self._pending_candidates = []
            self._set_occupied(False)
            return

        self._set_occupied(True)
        self._weight_buffer.append(weight)
        self._weight_buffer = self._weight_buffer[-5:]

        if not self._is_stable():
            return

        stable = round(weight, 2)

        if self._session_person is not None:
            self._set_person_weight(self._session_person, stable)
            return

        if not self._session_pending_fired:
            self._session_pending_fired = True
            self._fire_pending(stable)

    def _set_person_weight(self, person: str, weight: float) -> None:
        p = self.persons[person]
        if p.last_weight is not None and abs(p.last_weight - weight) < 0.005:
            return
        p.last_weight = weight
        async_dispatcher_send(self.hass, self.signal_person, person)

    def _fire_pending(self, weight: float) -> None:
        self._pending_weight = weight
        self._pending_candidates = list(self.persons.keys())
        async_dispatcher_send(self.hass, self.signal_pending)
        self.hass.bus.async_fire(
            EVENT_PENDING,
            {
                "weight": weight,
                "timestamp": time.time(),
                "persons": self._pending_candidates,
            },
        )
        _LOGGER.info("Bekleyen ölçüm: %.2f kg", weight)

    async def async_assign(self, person: str, weight: float | None = None) -> None:
        if person not in self.persons:
            raise ValueError(f"Bilinmeyen kişi: {person}")
        if weight is None:
            weight = self._pending_weight
        if weight is None:
            _LOGGER.warning("Atanacak ağırlık yok.")
            return
        self._set_person_weight(person, round(weight, 2))
        self._session_person = person
        self._pending_weight = None
        self._pending_candidates = []
        async_dispatcher_send(self.hass, self.signal_pending)