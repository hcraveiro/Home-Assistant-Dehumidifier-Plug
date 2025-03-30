# Home Assistant Dehumidifier Plug Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

Integrate plug-controlled dehumidifiers into your Home Assistant. This integration allows you to automate their operation based on humidity levels, energy usage, and a custom schedule.

- [Home Assistant Dehumidifier Plug Integration](#home-assistant-dehumidifier-plug-integration)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Entities](#entities)
  - [FAQ](#faq)

## Installation

This integration can be added as a custom repository in HACS. After installing it via HACS:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Dehumidifier Plug**.
3. Follow the configuration wizard.

## Configuration

For each dehumidifier you want to control, you must add a configuration entry. During the setup flow, you will be asked to select:

- A name for the dehumidifier.
- The plug switch entity.
- The power sensor entity (used to determine if the tank is full).
- The humidity sensor entity.
- The power threshold that indicates a full tank (e.g. 2W).
- The humidity level to start dehumidifying.
- The humidity level to stop dehumidifying.
- The time range during which the dehumidifier is allowed to operate.

You can change the humidity thresholds and schedule later via the **Configure** button in the integration.

## Entities

For each configured dehumidifier, the integration creates:

- `sensor.<name>_status`: shows one of the following states:
  - `Dehumidifying`
  - `Idle`
  - `Below target humidity`
  - `Outside dehumidifying hours`
  - `Full`

- `switch.<name>_control`: enables or disables automatic control logic for the dehumidifier.

These entities are attached to the same device as the selected plug switch or power sensor.

## FAQ

### How is the "Full" state detected?

When the plug is ON but the power consumption drops below the configured threshold (e.g. 2W), the integration assumes the tank is full.

### What happens if the dehumidifier is full?

The integration detects the "Full" state and stops issuing turn-off or turn-on commands until the user manually empties the tank. It will not automatically turn off the plug — it expects the device itself to stop drawing power.

### Can I change the humidity or schedule after setup?

Yes. Use the **Configure** option in the integration panel.

### Does the integration support multiple dehumidifiers?

Yes. You can add multiple config entries, each with their own independent settings and entities.