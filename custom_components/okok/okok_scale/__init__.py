from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_PERSON,
    ATTR_WEIGHT,
    CONF_PERSONS,
    DOMAIN,
    SERVICE_ASSIGN,
)
from .coordinator import TartiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

ASSIGN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_PERSON): cv.string,
        vol.Optional(ATTR_WEIGHT): vol.Coerce(float),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = TartiCoordinator(hass, entry)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_assign(call: ServiceCall) -> None:
        await coordinator.async_assign(
            call.data[ATTR_PERSON], call.data.get(ATTR_WEIGHT)
        )

    hass.services.async_register(
        DOMAIN, SERVICE_ASSIGN, _handle_assign, schema=ASSIGN_SCHEMA
    )

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coordinator: TartiCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
        hass.services.async_remove(DOMAIN, SERVICE_ASSIGN)
    return ok


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)