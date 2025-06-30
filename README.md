# Entity Receiver

A Home Assistant custom component that receives entity state broadcasts from other Home Assistant instances via UDP.

## Features

- **UDP Listener**: Listens for entity state broadcasts on a configurable UDP port
- **Dynamic Entity Creation**: Automatically creates sensors for received entities
- **Real-time Updates**: Updates entity states in real-time as broadcasts are received
- **Configuration UI**: Easy setup through Home Assistant's configuration interface
- **Entity Management**: Automatically removes stale entities that haven't been updated
- **Device Information**: Groups all received entities under a single device

## Installation

1. Copy the `entity_receiver` folder to your `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration → Integrations
4. Click "Add Integration" and search for "Entity Receiver"
5. Configure the UDP port (default: 8888) and broadcaster name

## Configuration

- **UDP Port**: The port to listen on for entity broadcasts (1024-65535)
- **Broadcaster Name**: A friendly name for the broadcasting Home Assistant instance
- **Poll Frequency**: How often to check for new UDP messages in milliseconds (10-10000ms, default: 100ms)

## Usage

Once configured, the integration will:

1. Listen for UDP broadcasts on the specified port
2. Automatically create sensors for each received entity
3. Update sensor states in real-time
4. Provide a status sensor showing the receiver state

## Entity Format

The component expects JSON messages in the following format:

```json
{
  "broadcaster_name": "Remote Home Assistant",
  "entity_id": "sensor.temperature",
  "state": "23.5",
  "attributes": {
    "friendly_name": "Living Room Temperature",
    "unit_of_measurement": "°C",
    "device_class": "temperature"
  }
}
```

## Troubleshooting

- Ensure the UDP port is not blocked by firewall
- Check that the broadcaster is sending to the correct IP and port
- Verify network connectivity between Home Assistant instances
- Check the logs for any error messages

## Changelog

### 1.0.0
- Initial release
- UDP listener functionality
- Dynamic entity creation
- Configuration flow
- Real-time updates
- Configurable poll frequency for UDP message checking
