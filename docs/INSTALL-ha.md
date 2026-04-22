# Install – Home Assistant (native API)

The Home Assistant variant uses ESPHome's native [API component][espapi]
so the gizmo appears as a device in HA with entities for battery %
(Plus 1.1 and S3) plus charging/USB voltage (S3 only). OTA updates,
logs, and reconfiguration all run through the [ESPHome Builder
add-on][ha-addon].

If you are not running Home Assistant, see
[INSTALL-standalone-web.md](INSTALL-standalone-web.md) or
[INSTALL-standalone-cli.md](INSTALL-standalone-cli.md) instead.

## What you need

- Home Assistant with the [ESPHome Builder add-on][ha-addon] installed
  and started ([official HA integration docs][ha-esphome])
- A [GitHub personal access token](../README.md#creating-a-github-token)
- A 2.4 GHz Wi-Fi network
- USB-C cable for the initial flash (subsequent updates run over
  Wi-Fi via [OTA][espota])

## 1. First device bootstrap

Home Assistant generates two secrets for you the first time it sees
the board. Start by creating a throw-away device:

1. In the ESPHome Builder web UI, click **+ NEW DEVICE**, pick any
   name, accept the defaults, and let it complete the first USB flash.
2. After the flash, open that device's YAML in the dashboard (**EDIT**
   on the tile). Copy the two auto-generated values for use in the
   next step:
   - `api:` → `encryption.key`
   - `wifi:` → `ap.password`

## 2. Populate `secrets.yaml`

Home Assistant stores all ESPHome secrets in a single shared file at
`/config/esphome/secrets.yaml` ([ESPHome secrets docs][espsecrets]).
Open it from the ESPHome dashboard (top-right menu → **Secrets**) or
via the [File editor add-on][ha-fileeditor] /
[Samba share][ha-samba] / [Studio Code Server][ha-vscode], then add
the `ghgizmo_*` keys from
[`secrets.yaml.example`](../secrets.yaml.example). Paste the two
values you copied above into `ghgizmo_api_encryption_key` and
`ghgizmo_ap_password`, then fill in the Wi-Fi, GitHub, and OTA keys.

`wifi_ssid` / `wifi_password` are normally already defined and
shared across every device on that HA install.

## 3. Install the gizmo firmware

1. Download the `-ha.yaml` file for your hardware from the latest
   [GitHub Release][releases]:

   | Device               | File                               |
   |----------------------|------------------------------------|
   | M5StickC Plus 1.1    | `ghmonitorgizmo-cplus-ha.yaml`     |
   | M5Stick S3 (K150)    | `ghmonitorgizmo-s3-ha.yaml`        |

2. Back in the ESPHome dashboard, click **EDIT** on the tile you
   created in step 1 and replace the entire contents with the
   downloaded YAML. Save.
3. Adjust the `substitutions:` block at the top (Wi-Fi static IP, IANA
   timezone, night-mode hours, etc.) to match your environment.
4. Click **INSTALL → Plug into the computer running ESPHome Dashboard**
   for the first flash. All subsequent installs can use **Wirelessly**.

Once it boots, HA auto-discovers the device as a new ESPHome
integration ([HA integration docs][ha-esphome]).

## Entities exposed

| Entity            | Plus 1.1 | S3  |
|-------------------|----------|-----|
| Battery Level (%) | ✅       | ✅  |
| Charging (bool)   | ❌       | ✅  |
| USB Voltage (V)   | ❌       | ✅  |

[espapi]: https://esphome.io/components/api
[espota]: https://esphome.io/components/ota/esphome
[espsecrets]: https://esphome.io/guides/faq.html#substitutions-and-secrets
[ha-esphome]: https://www.home-assistant.io/integrations/esphome/
[ha-addon]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=5c53de3b_esphome
[ha-fileeditor]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_configurator
[ha-samba]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_samba
[ha-vscode]: https://my.home-assistant.io/redirect/supervisor_addon/?addon=a0d7b954_vscode
[releases]: https://github.com/gjlumsden/gh-monitor-gizmo/releases/latest
