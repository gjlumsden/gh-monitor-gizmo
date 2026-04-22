# Install – Standalone, browser flash (no Home Assistant)

The standalone variant has **no** ESPHome API component. Instead it
exposes ESPHome's built-in [web_server component][espweb] on port 80
for monitoring and OTA updates, plus the [captive_portal
component][espcp] for first-boot Wi-Fi onboarding. This guide uses
[web.esphome.io][espweb-flash] to flash without installing anything
locally.

For the CLI-based route see
[INSTALL-standalone-cli.md](INSTALL-standalone-cli.md).  
If you use Home Assistant, use [INSTALL-ha.md](INSTALL-ha.md) instead.

## What you need

- Chrome, Edge, or any Chromium-based browser on a desktop with USB
  (Firefox and Safari don't implement Web Serial and are not supported
  by [web.esphome.io][espweb-flash])
- A [GitHub personal access token](../README.md#creating-a-github-token)
- A 2.4 GHz Wi-Fi network
- USB-C cable
- **CH9102F USB-serial driver** – both M5Stick boards use a WCH
  CH9102F bridge that isn't in the stock Windows/macOS driver set.
  Install it *before* plugging the device in, otherwise the
  `web.esphome.io` **Connect** dialog will show no serial ports. See
  [USB drivers](../README.md#usb-drivers-first-flash-only) in the
  main README.

## 1. Prepare a `secrets.yaml`

Copy [`secrets.yaml.example`](../secrets.yaml.example) to
`secrets.yaml` and fill in the values. You can skip
`ghgizmo_api_encryption_key` for standalone – the `-standalone.yaml`
builds never reference it ([ESPHome secrets docs][espsecrets]).

The `web_server` is **open on your LAN by default**. To require a
login, edit the built YAML and add an `auth:` block under
`web_server:` (username / password); see the [web_server docs][espweb].

## 2. Download and personalise the YAML

Grab the `-standalone.yaml` file for your hardware from the latest
[GitHub Release][releases]:

| Device               | File                                     |
|----------------------|------------------------------------------|
| M5StickC Plus 1.1    | `ghmonitorgizmo-cplus-standalone.yaml`   |
| M5Stick S3 (K150)    | `ghmonitorgizmo-s3-standalone.yaml`      |

Open it in any text editor and adjust the `substitutions:` block at
the top (Wi-Fi static IP, IANA timezone, night-mode hours, etc.).

## 3. Compile into a `.bin`

web.esphome.io installs pre-compiled `.bin` firmware; it does **not**
compile YAML. The simplest way to get a `.bin` is the [ESPHome
CLI][espcli-guide]:

```powershell
pipx install esphome   # or: pip install --user esphome
esphome compile ghmonitorgizmo-cplus-standalone.yaml
```

The resulting `factory.bin` lands under
`.esphome/build/<device-name>/.pioenvs/<device-name>/firmware.factory.bin`.
(If you prefer to skip the CLI entirely and flash with
`esphome run` instead, follow
[INSTALL-standalone-cli.md](INSTALL-standalone-cli.md).)

## 4. Flash in the browser

1. Plug the device into USB while holding the side button / boot
   button if required (the M5Stick boards typically auto-enter
   bootloader mode on their own).
2. Open [web.esphome.io][espweb-flash] and click **Connect**. Pick the
   USB serial port.
3. Click **Install** → **Choose File** → select the `firmware.factory.bin`.
4. Wait for the flash to complete and click **Next → Close**.

## 5. First-boot Wi-Fi (captive portal)

If the device can't reach the Wi-Fi you configured, it starts a
fallback access point named **GH Monitor Gizmo** secured with your
`ghgizmo_ap_password`. The [captive_portal component][espcp] redirects
any HTTP request to a setup page where you can pick an SSID and enter
a password – no reflash needed.

Connect to the AP, browse to <http://192.168.4.1>, fill in the form,
and the device reboots onto your network.

## 6. Using the web UI

Once on your LAN, browse to the device's IP (or
`ghmonitorgizmo.local` if mDNS resolves on your machine):

- Live state of every entity the firmware publishes
- Log stream
- OTA firmware upload (**Update** tab) – uses the same
  `ghgizmo_ota_password` secret ([OTA docs][espota])

For how the web UI looks and what it can do, see the
[web_server documentation][espweb].

[espweb]: https://esphome.io/components/web_server
[espcp]: https://esphome.io/components/captive_portal
[espwifi]: https://esphome.io/components/wifi
[espota]: https://esphome.io/components/ota/esphome
[espsecrets]: https://esphome.io/guides/faq.html#substitutions-and-secrets
[espweb-flash]: https://web.esphome.io/
[espcli-guide]: https://esphome.io/guides/getting_started_command_line
[releases]: https://github.com/gjlumsden/gh-monitor-gizmo/releases/latest
