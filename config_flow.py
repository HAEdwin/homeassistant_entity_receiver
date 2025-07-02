"""Config flow for Entity Receiver integration."""

import logging
import socket
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_UDP_PORT,
    CONF_BROADCASTER_NAME,
    DEFAULT_UDP_PORT,
    DEFAULT_BROADCASTER_NAME,
)

_LOGGER = logging.getLogger(__name__)


class EntityReceiverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Entity Receiver."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate port is not in use by checking if we can bind to it
            port = user_input[CONF_UDP_PORT]

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("", port))
                sock.close()
            except OSError:
                errors[CONF_UDP_PORT] = "port_in_use"

            if not errors:
                # Create unique ID based on port
                await self.async_set_unique_id(f"{DOMAIN}_{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Entity Receiver (Port {port})",
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_UDP_PORT, default=DEFAULT_UDP_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1024, max=65535)
                ),
                vol.Optional(
                    CONF_BROADCASTER_NAME, default=DEFAULT_BROADCASTER_NAME
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EntityReceiverOptionsFlowHandler(config_entry)


class EntityReceiverOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Entity Receiver."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle options flow."""
        errors = {}

        if user_input is not None:
            # Validate port if changed
            port = user_input.get(CONF_UDP_PORT, self.config_entry.data[CONF_UDP_PORT])

            if port != self.config_entry.data[CONF_UDP_PORT]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(("", port))
                    sock.close()
                except OSError:
                    errors[CONF_UDP_PORT] = "port_in_use"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_UDP_PORT,
                    default=self.config_entry.options.get(
                        CONF_UDP_PORT, self.config_entry.data[CONF_UDP_PORT]
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1024, max=65535)),
                vol.Optional(
                    CONF_BROADCASTER_NAME,
                    default=self.config_entry.options.get(
                        CONF_BROADCASTER_NAME,
                        self.config_entry.data.get(
                            CONF_BROADCASTER_NAME, DEFAULT_BROADCASTER_NAME
                        ),
                    ),
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
