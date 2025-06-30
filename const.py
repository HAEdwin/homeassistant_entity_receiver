"""Constants for the Entity Receiver integration."""

DOMAIN = "entity_receiver"

# Configuration keys
CONF_UDP_PORT = "udp_port"
CONF_BROADCASTER_NAME = "broadcaster_name"
CONF_POLL_FREQUENCY = "poll_frequency"

# Default values
DEFAULT_UDP_PORT = 8888
DEFAULT_BROADCASTER_NAME = "Remote Home Assistant"
DEFAULT_POLL_FREQUENCY = 100  # milliseconds

# Entity registry
ENTITY_REGISTRY_KEY = "entities"
