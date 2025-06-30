"""Coordinator for Entity Receiver integration."""

import asyncio
import json
import logging
import socket
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import (
    DOMAIN,
    CONF_UDP_PORT,
    CONF_BROADCASTER_NAME,
    CONF_POLL_FREQUENCY,
    DEFAULT_BROADCASTER_NAME,
    DEFAULT_POLL_FREQUENCY,
)

_LOGGER = logging.getLogger(__name__)


class EntityReceiverCoordinator(DataUpdateCoordinator):
    """Coordinator to manage UDP listener and entity data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),  # Cleanup interval
        )
        self.entry = entry
        self.port = entry.options.get(CONF_UDP_PORT, entry.data[CONF_UDP_PORT])
        self.broadcaster_name = entry.options.get(
            CONF_BROADCASTER_NAME,
            entry.data.get(CONF_BROADCASTER_NAME, DEFAULT_BROADCASTER_NAME),
        )
        self.poll_frequency = (
            entry.options.get(
                CONF_POLL_FREQUENCY,
                entry.data.get(CONF_POLL_FREQUENCY, DEFAULT_POLL_FREQUENCY),
            )
            / 1000.0
        )  # Convert milliseconds to seconds

        self._socket: Optional[socket.socket] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._last_seen: Dict[str, datetime] = {}

    @property
    def entities(self) -> Dict[str, Dict[str, Any]]:
        """Return current entities."""
        return self._entities

    async def async_start(self) -> None:
        """Start the UDP listener."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setblocking(False)
            self._socket.bind(("", self.port))

            self._listen_task = asyncio.create_task(self._listen_for_messages())
            _LOGGER.info("Started UDP listener on port %s", self.port)

        except Exception as err:
            _LOGGER.error("Failed to start UDP listener: %s", err)
            raise

    async def async_stop(self) -> None:
        """Stop the UDP listener."""
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        if self._socket:
            self._socket.close()
            self._socket = None

        _LOGGER.info("Stopped UDP listener")

    async def _listen_for_messages(self) -> None:
        """Listen for UDP messages with configurable polling frequency."""
        while True:
            try:
                # Use asyncio with timeout to allow configurable polling
                loop = asyncio.get_event_loop()

                try:
                    # Poll for messages with timeout based on poll frequency
                    data, addr = await asyncio.wait_for(
                        loop.sock_recvfrom(self._socket, 4096),
                        timeout=self.poll_frequency,
                    )

                    # Process the message immediately when received
                    await self._process_message(data, addr)

                except asyncio.TimeoutError:
                    # Timeout is expected - continue polling
                    continue

            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error receiving UDP message: %s", err)
                await asyncio.sleep(self.poll_frequency)  # Wait before retrying

    async def _process_message(self, data: bytes, addr: tuple) -> None:
        """Process received UDP message."""
        try:
            # Decode JSON message
            message = json.loads(data.decode("utf-8"))

            # Extract entity information
            entity_id = message.get("entity_id")
            if not entity_id or not isinstance(entity_id, str) or not entity_id.strip():
                _LOGGER.warning(
                    "Received message with invalid entity_id from %s: %s",
                    addr[0],
                    entity_id,
                )
                return

            # Store entity data
            self._entities[entity_id] = {
                "entity_id": entity_id,
                "state": message.get("state"),
                "attributes": message.get("attributes", {}),
                "broadcaster_name": message.get("broadcaster_name", "Unknown"),
                "source_ip": addr[0],
                "last_updated": datetime.now(),
            }

            self._last_seen[entity_id] = datetime.now()

            # Trigger update for any listening entities
            self.async_set_updated_data(self._entities)

            _LOGGER.debug(
                "Received entity update: %s = %s from %s",
                entity_id,
                message.get("state"),
                addr[0],
            )

        except json.JSONDecodeError as err:
            _LOGGER.warning("Failed to decode JSON from %s: %s", addr[0], err)
        except Exception as err:
            _LOGGER.error("Error processing message from %s: %s", addr[0], err)

    async def _async_update_data(self) -> Dict[str, Dict[str, Any]]:
        """Update data - cleanup old entities."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=10)  # Remove entities not seen for 10 minutes

        # Remove old entities
        old_entities = [
            entity_id
            for entity_id, last_seen in self._last_seen.items()
            if last_seen < cutoff
        ]

        for entity_id in old_entities:
            self._entities.pop(entity_id, None)
            self._last_seen.pop(entity_id, None)
            _LOGGER.debug("Removed stale entity: %s", entity_id)

        return self._entities

    @callback
    def get_entity_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific entity."""
        return self._entities.get(entity_id)
