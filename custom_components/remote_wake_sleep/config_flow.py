import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # Home Assistant < 2024.11
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .const import DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RemoteWakeSleepConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT

    async def _validate_connection(self, host: str, port: int) -> None:
        session = async_get_clientsession(self.hass)
        async with asyncio.timeout(5):
            async with session.get(f"http://{host}:{port}/targets") as resp:
                resp.raise_for_status()
                await resp.json()

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._validate_connection(user_input["host"], user_input["port"])
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{user_input['host']}:{user_input['port']}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Remote Wake/Sleep ({user_input['host']})",
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required("host", default=self._discovered_host or ""): str,
                vol.Required("port", default=self._discovered_port): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo):
        self._discovered_host = discovery_info.host
        self._discovered_port = discovery_info.port or DEFAULT_PORT

        await self.async_set_unique_id(f"{self._discovered_host}:{self._discovered_port}")
        self._abort_if_unique_id_configured()

        try:
            await self._validate_connection(self._discovered_host, self._discovered_port)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return self.async_abort(reason="cannot_connect")

        self.context["title_placeholders"] = {"host": self._discovered_host}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=f"Remote Wake/Sleep ({self._discovered_host})",
                data={"host": self._discovered_host, "port": self._discovered_port},
            )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"host": self._discovered_host},
        )
