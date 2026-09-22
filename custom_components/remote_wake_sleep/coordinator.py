import asyncio
import logging
from datetime import timedelta

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class RemoteWakeSleepCoordinator(DataUpdateCoordinator[dict[str, str]]):
    def __init__(self, hass: HomeAssistant, host: str, port: int, poll_interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self._host = host
        self._port = port
        self._session = async_get_clientsession(hass)

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def _get_json(self, path: str):
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with self._session.get(f"{self.base_url}{path}") as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _async_update_data(self) -> dict[str, str]:
        try:
            targets_response = await self._get_json("/targets")
            targets = targets_response.get("targets", [])

            data: dict[str, str] = {}
            for target in targets:
                status_response = await self._get_json(f"/{target}/get-status")
                data[target] = status_response.get("status", "unknown")
            return data
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with server: {err}") from err

    async def async_wake_up(self, target: str) -> None:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with self._session.get(f"{self.base_url}/{target}/wake-up") as resp:
                resp.raise_for_status()

    async def async_go_sleep(self, target: str) -> None:
        async with asyncio.timeout(REQUEST_TIMEOUT):
            async with self._session.get(f"{self.base_url}/{target}/go-sleep") as resp:
                resp.raise_for_status()
