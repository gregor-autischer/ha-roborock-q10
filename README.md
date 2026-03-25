# Roborock Q10 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom Home Assistant integration for controlling **Roborock Q10 series** robot vacuums (model `roborock.vacuum.ss07`), including the **Q10 S5+**.

> **Note:** This is a stopgap integration. The Q10 series uses Roborock's newer B01 protocol, which the [official Roborock integration](https://www.home-assistant.io/integrations/roborock/) does not yet support. Once official support lands, you should migrate to that and remove this integration.

## Supported Models

| Model | Internal ID | Status |
|---|---|---|
| Roborock Q10 S5+ | `roborock.vacuum.ss07` | Tested and working |
| Other Q10 variants | `roborock.vacuum.ss*` | Should work (untested) |

## Features

**Vacuum controls:**
- Start / Stop / Pause cleaning
- Return to dock (automatically stops cleaning first to prevent auto-resume)
- Fan speed control (Quiet, Balanced, Turbo, Max, Max+)
- Locate (beep)
- Send raw commands via `vacuum.send_command` service

**Sensors:**
- Battery level
- Main brush life remaining (%)
- Side brush life remaining (%)
- Filter life remaining (%)
- Sensor (cliff/wall) life remaining (%)

**Extra attributes on the vacuum entity:**
- Clean area, clean time, cleaning progress
- Water level, clean mode
- Fault code (when active)

**Status updates** are pushed in real-time via MQTT — no polling.

## Prerequisites

- [HACS](https://hacs.xyz/) installed on your Home Assistant instance
- A Roborock account (the email you use in the Roborock app)
- Your vacuum connected to Wi-Fi and visible in the Roborock app

## Installation

### Step 1: Add the repository to HACS

1. Open Home Assistant
2. Go to **HACS** > **Integrations**
3. Click the **three dots** menu (top right) > **Custom repositories**
4. Add this repository URL: `https://github.com/autischer/ha-roborock-q10`
5. Category: **Integration**
6. Click **Add**

### Step 2: Install the integration

1. In HACS, search for **Roborock Q10**
2. Click **Download**
3. **Restart Home Assistant**

### Step 3: Set up the integration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Roborock Q10**
3. Enter your **Roborock account email**
4. Check your email for a **verification code** and enter it
5. Done — your vacuum entity and sensors will appear

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=roborock_q10)

## How It Works

This integration uses the [python-roborock](https://github.com/Python-roborock/python-roborock) library to communicate with your vacuum via Roborock's cloud MQTT broker. A one-time cloud authentication is required to obtain device credentials. After that, commands and status updates flow through the MQTT connection.

If your credentials expire, Home Assistant will prompt you to re-authenticate — just enter your email and a new verification code.

## Troubleshooting

**Integration not showing up after install?**
- Make sure you restarted Home Assistant after installing via HACS.

**"No Q10 device found in account"?**
- Ensure your vacuum is set up in the Roborock app (not Mi Home) and appears online.

**Vacuum resumes cleaning after being sent to dock?**
- This is handled — the integration automatically stops the vacuum before sending it to dock. If you're calling services manually, send `vacuum.stop` before `vacuum.return_to_base`.

**Token expired / reauth needed?**
- Home Assistant will show a notification. Click it and follow the email + code flow again.

## Disclaimer

This integration communicates through the Roborock cloud. It is not affiliated with Roborock. Use at your own risk.

## License

MIT
