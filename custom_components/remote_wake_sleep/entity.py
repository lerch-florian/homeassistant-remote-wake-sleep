from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RemoteWakeSleepCoordinator


class RemoteWakeSleepEntity(CoordinatorEntity[RemoteWakeSleepCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: RemoteWakeSleepCoordinator, entry: ConfigEntry, target: str) -> None:
        super().__init__(coordinator)
        self._target = target
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{target}")},
            name=target,
        )

    @property
    def status(self) -> str:
        return (self.coordinator.data or {}).get(self._target, "unknown")
