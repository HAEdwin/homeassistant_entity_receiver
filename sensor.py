"""Sensor platform for Entity Receiver integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import EntityReceiverCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Entity Receiver sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Add the main receiver status sensor
    async_add_entities([EntityReceiverStatusSensor(coordinator, entry)])

    # Listen for new entities and add them dynamically
    @callback
    def async_add_entity_sensors():
        """Add sensors for new entities."""
        current_entities = set(coordinator.entities.keys())
        existing_sensors = {
            entity.entity_id.split(".")[-1]
            for entity in hass.data[DOMAIN].get(f"{entry.entry_id}_sensors", set())
            if hasattr(entity, "entity_id") and entity.entity_id is not None
        }

        new_entities = current_entities - existing_sensors

        if new_entities:
            new_sensors = []
            for entity_id in new_entities:
                if entity_id:  # Ensure entity_id is not None or empty
                    sensor = ReceivedEntitySensor(coordinator, entry, entity_id)
                    new_sensors.append(sensor)

            if new_sensors:
                async_add_entities(new_sensors)

                # Track added sensors
                if f"{entry.entry_id}_sensors" not in hass.data[DOMAIN]:
                    hass.data[DOMAIN][f"{entry.entry_id}_sensors"] = set()

                hass.data[DOMAIN][f"{entry.entry_id}_sensors"].update(new_sensors)

    # Set up the listener
    coordinator.async_add_listener(async_add_entity_sensors)


class EntityReceiverStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the status of the Entity Receiver."""

    def __init__(
        self, coordinator: EntityReceiverCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_status"
        self._attr_name = f"Entity Receiver Status (Port {coordinator.port})"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Entity Receiver (Port {self.coordinator.port})",
            manufacturer="Entity Receiver",
            model="UDP Receiver",
            sw_version="1.0.0",
        )

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if self.coordinator._socket and not self.coordinator._socket._closed:
            return "listening"
        return "stopped"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        return {
            "port": self.coordinator.port,
            "broadcaster_name": self.coordinator.broadcaster_name,
            "poll_frequency_ms": int(self.coordinator.poll_frequency * 1000),
            "entities_count": len(self.coordinator.entities),
            "entities": list(self.coordinator.entities.keys()),
        }

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        if self.native_value == "listening":
            return "mdi:antenna"
        return "mdi:antenna-off"


class ReceivedEntitySensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a received entity from the broadcaster."""

    def __init__(
        self,
        coordinator: EntityReceiverCoordinator,
        entry: ConfigEntry,
        entity_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._entry = entry

        # Validate entity_id
        if not entity_id:
            raise ValueError("entity_id cannot be None or empty")

        # Create a safe entity ID for Home Assistant
        safe_entity_id = entity_id.replace(".", "_").replace("-", "_")
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{safe_entity_id}"

        # Get entity data to set initial name
        entity_data = coordinator.get_entity_data(entity_id)
        if entity_data and entity_data.get("attributes", {}).get("friendly_name"):
            self._attr_name = f"Received {entity_data['attributes']['friendly_name']}"
        else:
            self._attr_name = f"Received {entity_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"Entity Receiver (Port {self.coordinator.port})",
            manufacturer="Entity Receiver",
            model="UDP Receiver",
            sw_version="1.0.0",
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._entity_id in self.coordinator.entities

    @property
    def native_value(self) -> Optional[str]:
        """Return the state of the received entity."""
        entity_data = self.coordinator.get_entity_data(self._entity_id)
        if entity_data:
            return entity_data.get("state")
        return None

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        entity_data = self.coordinator.get_entity_data(self._entity_id)
        if entity_data:
            return entity_data.get("attributes", {}).get("unit_of_measurement")
        return None

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class."""
        entity_data = self.coordinator.get_entity_data(self._entity_id)
        if entity_data:
            return entity_data.get("attributes", {}).get("device_class")
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        entity_data = self.coordinator.get_entity_data(self._entity_id)
        if not entity_data:
            return {}

        attributes = entity_data.get("attributes", {}).copy()

        # Add receiver-specific attributes
        attributes.update(
            {
                "original_entity_id": self._entity_id,
                "broadcaster_name": entity_data.get("broadcaster_name"),
                "source_ip": entity_data.get("source_ip"),
                "last_updated": entity_data.get("last_updated"),
            }
        )

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        entity_data = self.coordinator.get_entity_data(self._entity_id)
        if entity_data:
            # Try to get icon from attributes
            icon = entity_data.get("attributes", {}).get("icon")
            if icon:
                return icon

        # Default icon based on entity type
        if "temperature" in self._entity_id.lower():
            return "mdi:thermometer"
        elif "humidity" in self._entity_id.lower():
            return "mdi:water-percent"
        elif "light" in self._entity_id.lower():
            return "mdi:lightbulb"
        elif "switch" in self._entity_id.lower():
            return "mdi:toggle-switch"
        else:
            return "mdi:broadcast"
