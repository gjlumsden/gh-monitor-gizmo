# Install – Standalone, ESPHome CLI (no Home Assistant)

This path uses the [standalone ESPHome CLI][esphome-install] to
compile, flash, and OTA-update the standalone variant. The resulting
firmware has no ESPHome API – it publishes everything via the
built-in [web_server][espweb] on port 80 and offers
[captive_portal][espcp] fallback for Wi-Fi onboarding.

For browser-only flashing use
[INSTALL-standalone-web.md](INSTALL-standalone-web.md).  
For Home Assistant use [INSTALL-ha.md](INSTALL-ha.md).

## What you need

- Python 3.10+
- [ESPHome][esphome] 2026.4 or later (`pipx install esphome`)
- A [GitHub personal access token](../README.md#creating-a-github-token)
- A 2.4 GHz Wi-Fi network
- USB-C cable for the first flash
- **USB-serial driver** (M5StickC Plus 1.1 on Windows / macOS only –
  needs the FTDI VCP driver). The M5Stick S3 uses native ESP32-S3 USB
  and needs no driver on any platform. See
  [USB-serial driver](../README.md#4-install-the-usb-serial-driver-first-flash-only)
  in the main README.

## 1. Clone and configure

```powershell
git clone https://github.com/gjlumsden/gh-monitor-gizmo.git
cd gh-monitor-gizmo
copy secrets.yaml.example secrets.yaml
notepad secrets.yaml   # fill in values
```

You can skip `ghgizmo_api_encryption_key` – the standalone variant
never references it ([ESPHome secrets][espsecrets]).

## 2. Build the single-file YAMLs

The firmware is stored as source templates with shared fragments in
`common/`. [`build.py`](../build.py) inlines them into four
self-contained YAMLs under `dist/`:

```powershell
python build.py
# dist/ghmonitorgizmo-cplus-ha.yaml
# dist/ghmonitorgizmo-cplus-standalone.yaml
# dist/ghmonitorgizmo-s3-ha.yaml
# dist/ghmonitorgizmo-s3-standalone.yaml
```

`build.py` uses only the Python standard library (no `pip install`
required).

## 3. Personalise

Open the `-standalone.yaml` matching your hardware and tweak the
`substitutions:` block at the top (Wi-Fi static IP, IANA timezone,
night-mode hours, backlight brightness, etc.).

The `web_server` is open on your LAN by default. Add an `auth:` block
under `web_server:` in
[`common/variants/standalone/api.yaml`](../common/variants/standalone/api.yaml)
and rebuild if you want basic-auth – see the
[web_server docs][espweb] for syntax.

## 4. Flash over USB

Plug the device in and run [`esphome run`][espcli-guide]:

```powershell
# Plus 1.1
esphome run dist/ghmonitorgizmo-cplus-standalone.yaml

# S3
esphome run dist/ghmonitorgizmo-s3-standalone.yaml
```

ESPHome compiles, picks up the serial port, writes the firmware, and
starts streaming logs.

## 5. Subsequent updates (OTA)

Later builds can go over Wi-Fi using the
[`ota.esphome` component][espota] and the `ghgizmo_ota_password`
secret:

```powershell
esphome run dist/ghmonitorgizmo-cplus-standalone.yaml --device ghmonitorgizmo.local
esphome run dist/ghmonitorgizmo-s3-standalone.yaml    --device ghmonitorgizmo-s3.local
```

The device's web UI (**Update** tab) accepts uploaded `.bin` files as
an alternative OTA path.

## 6. First-boot Wi-Fi (captive portal)

If the device cannot reach the configured Wi-Fi at boot, it starts a
fallback access point named **GH Monitor Gizmo** using
`ghgizmo_ap_password`. Connecting to it lands on a captive portal at
<http://192.168.4.1>. See [captive_portal][espcp] and [wifi][espwifi].

[esphome]: https://esphome.io/
[esphome-install]: https://esphome.io/guides/installing_esphome
[espcli-guide]: https://esphome.io/guides/getting_started_command_line
[espweb]: https://esphome.io/components/web_server
[espcp]: https://esphome.io/components/captive_portal
[espwifi]: https://esphome.io/components/wifi
[espota]: https://esphome.io/components/ota/esphome
[espsecrets]: https://esphome.io/guides/faq.html#substitutions-and-secrets
