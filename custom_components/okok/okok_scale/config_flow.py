from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_PERSONS, CONF_PERSON_NAME, CONF_SCALE_MAC, DOMAIN, NAME


class TartiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            mac = user_input[CONF_SCALE_MAC].strip().upper()
            await self.async_set_unique_id(mac.replace(":", ""))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{NAME} ({mac})",
                data={CONF_SCALE_MAC: mac, CONF_PERSONS: []},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_SCALE_MAC): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return TartiOptionsFlow(entry)


class TartiOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry
        self._persons = list(
            entry.options.get(CONF_PERSONS, entry.data.get(CONF_PERSONS, []))
        )

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init", menu_options=["add_person", "remove_person"]
        )

    async def async_step_add_person(self, user_input=None):
        if user_input is not None:
            self._persons.append(
                {CONF_PERSON_NAME: user_input[CONF_PERSON_NAME].strip()}
            )
            self._save()
            return await self.async_step_init()
        return self.async_show_form(
            step_id="add_person",
            data_schema=vol.Schema({vol.Required(CONF_PERSON_NAME): str}),
        )

    async def async_step_remove_person(self, user_input=None):
        if not self._persons:
            return await self.async_step_init()
        if user_input is not None:
            self._persons = [
                p for p in self._persons if p[CONF_PERSON_NAME] != user_input["person"]
            ]
            self._save()
            return await self.async_step_init()
        choices = {p[CONF_PERSON_NAME]: p[CONF_PERSON_NAME] for p in self._persons}
        return self.async_show_form(
            step_id="remove_person",
            data_schema=vol.Schema({vol.Required("person"): vol.In(choices)}),
        )

    def _save(self) -> None:
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, CONF_PERSONS: self._persons},
        )