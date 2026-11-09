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
- **Low-power timeout** — seconds of continuously observed low power before the tank is considered possibly full (default: 60 seconds).
- **Notifications** — optionally select one or more Home Assistant mobile app notification services. One notification is sent when a new possible-full condition is detected.

The difference between the two humidity limits provides hysteresis to reduce unnecessary switching.
The lower limit must be strictly below the upper limit. Readings must be numeric and finite; humidity must be in the range 0–100%. Power in W or kW is supported.

### Weekly schedule and operating intervals

- Select one or more **Days of the week** for automatic operation.
- Under **Operating intervals**, add or remove as many start/end time pairs as required.
- Multiple intervals on the same day are supported; the dehumidifier can stop between them and restart when the next interval begins, subject to humidity and other control conditions.
- Intervals crossing midnight are supported. For example, Monday 22:00–02:00 remains eligible until Tuesday 02:00, even when Tuesday is not selected.
- Start times are inclusive; end times are exclusive.
- Equal start and end times mean the entire selected calendar day, not a zero-length interval.
- By default, every weekday is selected and the operating interval is **09:00–20:00**.

The schedule restricts **automatic** operation. Humidity thresholds, the automatic-control switch, full-tank detection and manual-override behavior also influence whether the plug is turned on or off. Manually enabled operation may be retained outside scheduled hours under the existing override rules.

### Optional window and door interlock

Select one or more **Window sensors** in setup or Configure. The selector accepts binary sensors with the **opening**, **window**, or **door** device class. No sensors are selected by default; clearing the list in Options removes the interlock.

- Any known open sensor (`on`, or `open`) blocks automatic starts and turns off an observed running plug while automatic control is enabled. Multiple sensors use **any-open** logic; all must be known closed (`off`, or `closed`) before normal control resumes.
- An open sensor takes priority even if another window sensor is missing, unknown, unavailable, or invalid. It also takes priority over manual starts, scheduled hours, and full-tank status. A manual start while automatic control is enabled will therefore be stopped again on the next update.
- If no sensor is known open and any selected sensor is missing, unknown, unavailable, or invalid, the update fails and automatic commands pause under the normal dependency-fault policy. An already-running plug may remain on. The integration retries automatically.
- A known open sensor can still stop a positively observed running plug when a power or humidity dependency has failed. The update then remains failed/unavailable until those dependencies recover. An unknown or unavailable plug state cannot safely be controlled.
- With **automatic control disabled** (or not yet restored at startup), the integration sends no commands, including window-related stops. Window observations remain available as attributes when readings are valid.
- Closing windows does **not** restore an interrupted cycle. Normal start conditions apply: inside the schedule, automatic control enabled, no full-tank block, and humidity strictly above the upper limit. With the default 50%/60% limits, a cycle interrupted at **55% stays off** after closing, including at exactly 60%, until humidity exceeds 60%.

Window changes are checked by periodic coordinator polling (Home Assistant's default scan interval, normally **30 seconds**), not immediate state-change listeners. Allow up to a polling interval plus scheduling, service and device-reporting delays; outages can extend this further. This is a convenience interlock, not a safety mechanism. Service completion does not guarantee immediate device feedback.

### Editing an existing installation

Go to **Settings → Devices & Services → Dehumidifier Plug → Configure**.

You can change the Plug Switch, Power Sensor, Humidity Sensor, all thresholds, selected weekdays and operating intervals without deleting and recreating the integration.

Saving Options triggers a reload of that configuration entry. If a previous configuration is missing a required entity, select it through Configure to recover the entry.

## Entities

Each configured dehumidifier creates:

- `sensor.<name>_status` — displays **Window open**, **Full**, **Dehumidifying**, **Automatic control disabled**, **Outside dehumidifying hours**, **Below target humidity**, or **Idle**. Its attributes expose the control decisions independently, including `windows_open`. **Window open** has highest status priority when automatic control is enabled, even if a stop is awaiting device feedback; otherwise the existing Full → Dehumidifying → Automatic control disabled → Outside hours → Below target → Idle priority applies. Failed updates make the entity unavailable rather than presenting stale decisions as healthy.
- `switch.<name>_control` — enables or disables automatic dehumidifier control. Its state is restored after a Home Assistant restart when a previous state is available.

Entity IDs are derived from the configured name and may differ when Home Assistant resolves naming collisions or existing registry entries.

### Full-tank detection

When the plug is on and measured power remains **below** the configured minimum-power threshold for the configured timeout, the status becomes **Full**. Low consumption is only an indication; it may have other causes. Evaluation occurs on coordinator updates, so detection may take longer than the timeout. A sensor outage or restart interrupts the low-power observation timer. The integration does not necessarily switch off the plug; the device is expected to stop its own dehumidification cycle. The detection state is cleared when measured power recovers or the plug is switched off. A notification is sent only on entry into a newly detected full state, not on every update; delivery is best-effort.

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

**What if the plug or a sensor becomes unavailable?** The integration remains loaded, while the control switch and status sensor become unavailable. No automatic commands are issued while a required reading is invalid, except that a known open window can stop a positively observed running plug with automatic control enabled (see the interlock policy above). In particular, an already-on plug may remain on beyond its schedule until readings recover. The integration retries automatically; the log identifies the failing dependency or reading. When readings return, control resumes using the restored automatic-control setting.

**Will the integration notify me immediately?** Detection is based on periodic updates, not a real-time timer. Mobile app notifications must be enabled and recipients selected in Configure; they are off by default.

## Development and tests

GitHub Actions runs automated tests and checks branch coverage. The enforced minimums are **95%** for scheduling/configuration models, **78%** for the coordinator and **88%** for setup/configuration flows, entities and utilities. These percentages are measured for the specified modules rather than the entire repository.
