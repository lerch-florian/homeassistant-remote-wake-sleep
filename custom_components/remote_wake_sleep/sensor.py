from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import RemoteWakeSleepEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_targets: set[str] = set()

    def _add_new_entities() -> None:
        new_targets = set(coordinator.data or {}) - known_targets
        if not new_targets:
            return
        known_targets.update(new_targets)
        async_add_entities(
            RemoteWakeSleepStatusSensor(coordinator, entry, target) for target in new_targets
        )

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class RemoteWakeSleepStatusSensor(RemoteWakeSleepEntity, SensorEntity):
    _attr_name = "Status"

    def __init__(self, coordinator, entry: ConfigEntry, target: str) -> None:
        super().__init__(coordinator, entry, target)
        self._attr_unique_id = f"{entry.entry_id}_{target}_status"

    @property
    def native_value(self) -> str:
        return self.status
