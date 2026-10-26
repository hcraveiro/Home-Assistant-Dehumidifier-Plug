# Home Assistant Dehumidifier Plug Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Control plug-connected dehumidifiers in Home Assistant based on humidity, measured power consumption and a configurable weekly schedule. Each dehumidifier has independent settings.

## Installation

Add this repository as a **custom integration** in HACS, install **Dehumidifier Plug**, and restart Home Assistant. Then open **Settings → Devices & Services → Add Integration**, search for **Dehumidifier Plug**, and complete the setup flow.

## Configuration

Each dehumidifier requires:

- **Name** — a descriptive name for the installation.
- **Plug Switch** — a `switch` entity controlling the dehumidifier.
- **Power Sensor** — a `sensor` entity measuring plug power consumption in watts.
- **Humidity Sensor** — a `sensor` entity reporting relative humidity.
- **Minimum Power Threshold (W)** — power below this level while the plug is on indicates a potentially full tank (default: 2 W).
- **Upper Humidity Limit (%)** — automatic operation starts when humidity rises **above** this value (default: 60%).
- **Lower Humidity Limit (%)** — automatic operation stops when humidity falls **below** this value (default: 50%).

The difference between the two humidity limits provides hysteresis to reduce unnecessary switching.

### Weekly schedule and operating intervals

- Select one or more **Days of the week** for automatic operation.
- Under **Operating intervals**, add or remove as many start/end time pairs as required.
- Multiple intervals on the same day are supported; the dehumidifier can stop between them and restart when the next interval begins, subject to humidity and other control conditions.
- Intervals crossing midnight are supported. For example, Monday 22:00–02:00 remains eligible until Tuesday 02:00, even when Tuesday is not selected.
- Start times are inclusive; end times are exclusive.
- By default, every weekday is selected and the operating interval is **09:00–20:00**.

The schedule restricts **automatic** operation. Humidity thresholds, the automatic-control switch, full-tank detection and manual-override behavior also influence whether the plug is turned on or off. Manually enabled operation may be retained outside scheduled hours under the existing override rules.

### Editing an existing installation

Go to **Settings → Devices & Services → Dehumidifier Plug → Configure**.

You can change the Plug Switch, Power Sensor, Humidity Sensor, all thresholds, selected weekdays and operating intervals without deleting and recreating the integration.

Saving Options triggers a reload of that configuration entry. If a previous configuration is missing a required entity, select it through Configure to recover the entry.

## Entities

Each configured dehumidifier creates:

- `sensor.<name>_status` — displays **Full**, **Dehumidifying**, **Outside dehumidifying hours**, **Below target humidity**, or **Idle**.
- `switch.<name>_control` — enables or disables automatic dehumidifier control. Its state is restored after a Home Assistant restart when a previous state is available.

Entity IDs are derived from the configured name and may differ when Home Assistant resolves naming collisions or existing registry entries.

### Full-tank detection

When the plug is on and measured power remains **below** the configured minimum-power threshold for at least **60 seconds**, the status becomes **Full**. This state prevents automatic start commands while the condition persists. The integration does not physically empty the tank or necessarily switch off the plug; the device is expected to stop its own dehumidification cycle. The detection state is cleared when measured power recovers or the plug is switched off.

## Upgrading to v1.1.0

Existing installations from **v1.0.5** can be upgraded without deleting their configuration entries.

- An existing single start/end time interval is retained.
- If no weekdays were previously configured, all seven days are selected by default.
- Existing plug, power and humidity entities, as well as humidity/power thresholds, are retained.
- Existing manual override and full-tank detection behavior remains unchanged.

After upgrading, open **Configure** to inspect the migrated settings and optionally select weekdays and add operating intervals.

## FAQ

**Can I configure multiple dehumidifiers?** Yes. Create a separate integration entry for each dehumidifier.

**Does selecting a weekday guarantee that the device turns on?** No. The day and time interval must match, automatic control must be enabled, humidity must exceed the upper threshold, and the full-tank condition must not block automatic starting.

**Can I change the plug or sensors?** Yes. Open **Configure** and select the replacement entities.

**What if a sensor becomes unavailable?** The coordinator reports an update failure rather than issuing new automatic commands based on an invalid reading.

## Development and tests

GitHub Actions runs automated tests and checks branch coverage. The enforced minimums are **95%** for scheduling/configuration models, **78%** for the coordinator and **88%** for setup/configuration flows, entities and utilities. These percentages are measured for the specified modules rather than the entire repository.
