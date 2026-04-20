# GitHub Monitor Gizmo

[![ESPHome](https://img.shields.io/badge/ESPHome-2026.4%2B-black?logo=esphome&logoColor=white)][esphome]
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-compatible-41BDF5?logo=home-assistant&logoColor=white)][ha-esphome]
[![M5StickC Plus 1.1](https://img.shields.io/badge/device-M5StickC%20Plus%201.1-red)][m5]
[![Built with Copilot](https://img.shields.io/badge/built%20with-GitHub%20Copilot-24292e?logo=github-copilot&logoColor=white)](https://github.com/features/copilot)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

An [ESPHome][esphome] firmware for an [M5StickC Plus 1.1][m5] that turns
it into a desk-top GitHub activity monitor. It polls your user events
feed, carousels through anything new, beeps on CI failures, bounces a
Material Design GitHub logo around the screen when idle, and shows
battery %.

> Only tested on the **M5StickC Plus 1.1**. It should in principle
> work on any ESP32 with an ST7789V-compatible display and a buzzer,
> but you'll need to adjust pins, dimensions, and drop the AXP192
> battery sensor.

![gh-monitor-gizmo running on an M5StickC Plus 1.1](images/m5stick-cplus-1.1-gh-gizmo.png)

## Features

- **Events carousel** – shows each new event since the last poll in
  turn, one card every 5 s, with a bottom-of-screen progress dot row.
  Press the front M5 button to dismiss and return to idle.
- **Per-event detail** – headline (e.g. `Deleted branch`, `PR`,
  `CI FAIL`) plus a second line with branch/ref or PR/issue number and
  repo name.
- **CI tally** – running / success / failed counts across the last
  page, right-aligned in the header with Material Design icons.
- **Copilot detection** – highlights events where the actor, PR
  author, requested reviewer, commenter, or workflow triggering actor
  contains "copilot" (case-insensitive).
- **Audio cues** – short "ping" on new events, distinct "fail" tune on
  a CI failure.
- **Idle DVD-bouncer** – the GitHub logo bounces around the screen
  and cycles colour on each wall hit.
- **Battery %** – read from the on-board AXP192 PMIC over I²C and
  exposed to Home Assistant as a sensor.

## Hardware

- [M5StickC Plus 1.1][m5] (ESP32-PICO, 135×240 ST7789V, AXP192,
  buzzer, front "M5" button, side button, IR, mic)
- USB-C cable for the initial flash and power

## Prerequisites

- [ESPHome][esphome] 2026.4 or later – either the
  [Home Assistant ESPHome Builder add-on][ha-addon] (easiest) or the
  [standalone ESPHome CLI][esphome-install]
- A GitHub personal access token – see
  [Creating a GitHub token](#creating-a-github-token)
- A 2.4 GHz Wi-Fi network the device can reach

## Installation

### Option 1 – Home Assistant ESPHome Builder (recommended)

This is the easiest path: Home Assistant handles both the first USB
flash and subsequent OTA updates.

1. Install the [ESPHome Builder add-on][ha-addon] from
   **Settings → Add-ons → Add-on Store**. Start it and open the web UI.
2. Click **+ NEW DEVICE**, pick any name, accept the defaults, and let
   it do the initial flash. This does two useful things:
   - Puts the board into a known-good ESPHome state and gives you a
     working USB toolchain.
   - Writes a default **API encryption key** and **AP password** into
     Home Assistant's `/config/esphome/secrets.yaml`.
3. Open your Home Assistant `/config/esphome/secrets.yaml` (via the
   [File editor add-on][ha-fileeditor], the
   [Samba share add-on][ha-samba], or
   [Studio Code Server][ha-vscode]). The ESPHome Builder will have
   added entries for the new device &mdash; either named plainly
   (`api_encryption_key`, `ap_password`) or prefixed with the device
   name. Leave them in place and **add** `ghgizmo_*` entries alongside,
   copying the generated values across. Use
   [`secrets.yaml.example`](secrets.yaml.example) as a template for
   the remaining Wi-Fi, GitHub, and OTA keys.
4. Back in the ESPHome dashboard, click **EDIT** on the tile you just
   created and replace the entire contents with
   [`ghmonitorgizmo.yaml`](ghmonitorgizmo.yaml) from this repo. Save.
5. Click **INSTALL → Plug into the computer running ESPHome Dashboard**
   for the first flash. All subsequent installs
   can use **Wirelessly**.

After install, the device auto-discovers as a new ESPHome integration
and exposes a **Battery Level** sensor.

### Option 2 – ESPHome CLI

```powershell
pipx install esphome   # or: pip install --user esphome

git clone https://github.com/gjlumsden/gh-monitor-gizmo.git
cd gh-monitor-gizmo
copy secrets.yaml.example secrets.yaml
notepad secrets.yaml   # fill in the values

# first flash over USB
esphome run ghmonitorgizmo.yaml

# later updates over Wi-Fi
esphome run ghmonitorgizmo.yaml --device ghmonitorgizmo.local
```

Full CLI docs: <https://esphome.io/guides/getting_started_command_line>

## Creating a GitHub token

The device polls `GET /users/{user}/events`. That endpoint works with:

- **Fine-grained PAT**: `Metadata: Read-only` is sufficient for your
  own public events (and is granted to every fine-grained PAT by
  default); add repo-level access for private-repo events.
- **Classic PAT**: no scopes needed for public events; add `repo` to
  see private repo activity.

Create one at <https://github.com/settings/tokens>. Put it in
`secrets.yaml` as `ghgizmo_github_token`. The device only uses it to
raise the rate limit; it's sent over HTTPS to `api.github.com`.

## secrets.yaml

All secrets live in an ESPHome `secrets.yaml`. With the HA add-on this
is shared across every ESPHome device at `/config/esphome/secrets.yaml`
– Wi-Fi credentials are typically already there. You only need to add
the `ghgizmo_*` entries:

| Key | Purpose |
|-----|---------|
| `wifi_ssid` / `wifi_password` | Shared Wi-Fi (not prefixed; re-used across devices) |
| `ghgizmo_github_user` | Your GitHub username |
| `ghgizmo_github_token` | Personal access token |
| `ghgizmo_api_encryption_key` | ESPHome ↔ Home Assistant encryption key |
| `ghgizmo_ota_password` | OTA update password |
| `ghgizmo_ap_password` | Fallback AP password (if Wi-Fi unavailable) |

See [`secrets.yaml.example`](secrets.yaml.example) for the template.

## Configuration notes

- `ghmonitorgizmo.yaml` sets `verify_ssl: false` because mbedTLS on
  ESP-IDF doesn't ship the GitHub CA chain by default. All GitHub
  traffic still goes over TLS; only chain verification is skipped.
- **Wi-Fi**: the device is a 2.4 GHz-only ESP32. It needs an SSID
  that's broadcast on 2.4 GHz (if your router advertises the same
  SSID on both bands, that's fine), with WPA2-Personal or
  WPA2/WPA3-mixed. WPA3-only and Enterprise (802.1X) networks are
  **not** supported. Credentials come from the shared ESPHome
  `wifi_ssid` / `wifi_password` in `secrets.yaml`. If the primary
  network is unreachable at boot, the device brings up a fallback
  access point with the SSID `GH Monitor Gizmo` and the password
  from `ghgizmo_ap_password` – connect to it and browse to
  `http://192.168.4.1` to reconfigure.
- Static IP is set via the `static_ip` / `gateway` / `subnet` / `dns1`
  / `dns2` **substitutions** at the top of `ghmonitorgizmo.yaml`.
  Adjust them to match your network, or delete the `manual_ip:` block
  under `wifi:` entirely to use DHCP instead.
- Poll interval is 90 s with a 30 s startup delay. Tune via the
  `interval:` block; mind the GitHub 5000 req/hr user rate limit.
- Memory tuning lives in `esp32.framework.sdkconfig_options`. Do **not**
  add `bluetooth_proxy:` – the ESP-IDF HTTP client needs a contiguous
  allocation that a running BLE stack tends to fragment out of
  existence.

## Controls

| Input | Action |
|-------|--------|
| Front **M5** button (GPIO37) | Dismiss current event card → return to idle |
| Side button (GPIO39) | Unused (wire up in `binary_sensor:` if you want) |
| Reset (left side) | Hardware reset |

## Screen layout

```
 ┌──────────────────────────────────────┐
 │ GitHub   87%        [↻3 ✓5 ✗1]       │  ← header
 │                                      │
 │          Deleted branch              │  ← headline (colour-coded)
 │        copilot/fix-7  oura-mcp       │  ← detail (branch + repo)
 │                                      │
 │                                      │
 │ A: dismiss        • • ● • •          │  ← hint + carousel dots
 └──────────────────────────────────────┘
```

## Troubleshooting

- **`HTTP_CLIENT: Allocation failed`** – heap fragmentation. Reduce
  `buffer_size_rx` and `max_response_buffer_size` in `http_request:`,
  or reduce `per_page=` in the URL.
- **`user json parse failed: IncompleteInput`** – `max_response_buffer_size`
  is smaller than the response body. Raise it (currently 12 288).
- **`interval took a long time (>1 s)`** – usually the JSON parse on
  the 8 KB response. Harmless log noise.
- **Nothing shown after boot** – the device waits 30 s for Wi-Fi, then
  polls. On first fetch only the top event is shown as proof of life;
  after that, only genuinely new events trigger a carousel.
- **Battery reads 100 % with USB plugged** – that's the AXP192's raw
  voltage crossing the upper bound of the 3.3–4.2 V mapping.

## Development

For editing the YAML locally, the
[ESPHome VS Code extension][vscode-ext] is very useful – it gives you
schema validation, autocomplete, and inline docs for every component.

## Further reading

- [ESPHome documentation][esphome]
- [Home Assistant ESPHome integration][ha-esphome]
- [ESPHome Builder add-on (HA)][ha-addon]
- [M5StickC Plus 1.1 hardware docs][m5]
- [GitHub Events API][gh-events]

## Licence

[MIT](LICENSE)

[m5]: https://docs.m5stack.com/en/core/m5stickc_plus
[esphome]: https://esphome.io/
[esphome-install]: https://esphome.io/guides/installing_esphome
[ha-addon]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=5c53de3b_esphome
[ha-esphome]: https://www.home-assistant.io/integrations/esphome/
[ha-fileeditor]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_configurator
[ha-samba]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_samba
[ha-vscode]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_vscode
[gh-events]: https://docs.github.com/en/rest/activity/events
[vscode-ext]: https://marketplace.visualstudio.com/items?itemName=ESPHome.esphome-vscode
