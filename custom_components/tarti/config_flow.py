from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import CONF_PERSON_NAME, CONF_PERSONS, CONF_SCALE_ADDRESS, DOMAIN, NAME


class TartiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            addr = user_input[CONF_SCALE_ADDRESS].strip().upper()
            await self.async_set_unique_id(addr.replace(":", "").replace("-", ""))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=NAME,
                data={CONF_SCALE_ADDRESS: addr, CONF_PERSONS: []},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_SCALE_ADDRESS): str}),
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
            step_id="init",
            menu_options=["add_person", "remove_person"],
        )

    async def async_step_add_person(self, user_input=None):
        if user_input is not None:
            self._persons.append(
                {CONF_PERSON_NAME: user_input[CONF_PERSON_NAME].strip()}
            )
            return self.async_create_entry(
                title="",
                data={**self.entry.options, CONF_PERSONS: self._persons},
            )
        return self.async_show_form(
            step_id="add_person",
            data_schema=vol.Schema({vol.Required(CONF_PERSON_NAME): str}),
        )

    async def async_step_remove_person(self, user_input=None):
        if not self._persons:
            return self.async_create_entry(title="", data=self.entry.options)
        if user_input is not None:
            self._persons = [
                p for p in self._persons if p[CONF_PERSON_NAME] != user_input["person"]
            ]
            return self.async_create_entry(
                title="",
                data={**self.entry.options, CONF_PERSONS: self._persons},
            )
        choices = {p[CONF_PERSON_NAME]: p[CONF_PERSON_NAME] for p in self._persons}
        return self.async_show_form(
            step_id="remove_person",
            data_schema=vol.Schema({vol.Required("person"): vol.In(choices)}),
        )