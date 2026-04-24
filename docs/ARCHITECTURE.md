# Architecture & internals

Background for contributors. Covers the build pipeline, feature-gate
pattern, Dependabot integration quirks, night-mode behaviour, and a
short crash-debug history. Read this instead of reverse-engineering
the YAML.

If you only want to flash a pre-built image, the
[top-level README](../README.md) and the
[install guides](#see-also) have you covered.

## Contents

- [Dual-variant build](#dual-variant-build)
- [Paste-and-flash via `dist/`](#paste-and-flash-via-dist)
- [`build.py` flow](#buildpy-flow)
- [Feature-gate pattern (substitutions)](#feature-gate-pattern-substitutions)
- [Dependabot REST integration](#dependabot-rest-integration)
- [Night-mode beep suppression](#night-mode-beep-suppression)
- [Crash-debug history](#crash-debug-history)
- [Hardware audits](#hardware-audits)
- [See also](#see-also)

## Dual-variant build

Every supported device produces **two** flashable artefacts. The two
variants share 100% of the GitHub polling logic, display code, and UI
scripts — they differ only in how the device exposes itself on the
LAN.

| Variant        | `common/variants/...`             | Exposes                                       | When to choose                                      |
|----------------|------------------------------------|-----------------------------------------------|-----------------------------------------------------|
| `-ha`          | `common/variants/ha/api.yaml`      | ESPHome [native API][espapi] (port 6053)      | You already run Home Assistant and want entities    |
| `-standalone`  | `common/variants/standalone/api.yaml` | ESPHome [web server][espweb] + [captive portal][espcp] | You don't run HA, or you want to flash from a browser only |

The `-ha` variant **requires** a reachable Home Assistant instance to
receive the published battery / charging / USB-voltage sensors. It
will still run without one (the UI works fine), but the native API
will log repeated connection attempts and you lose the point of the
variant. Pick `-standalone` if you aren't running HA.

See [#9][i9] for the planned migration of the variant split away from
text templating and toward the community-standard `packages:` +
runtime config approach.

## Paste-and-flash via `dist/`

End users never read the `common/*.yaml` fragments or the
`.yaml.src` device templates. They grab one file:

```
dist/ghmonitorgizmo-{device}-{variant}.yaml
```

Each `dist/` YAML is a **single self-contained document** with every
`# !include` already inlined. That means:

- No `packages:` resolution happens at flash time.
- It pastes cleanly into the Home Assistant ESPHome Builder add-on,
  `esphome run`, or [web.esphome.io][espweb-flash] with no extra
  files on disk beside `secrets.yaml`.
- A newcomer can diff the single file against the upstream release
  YAML to see everything that actually runs on the device.

The trade-off is that the `dist/` files are **generated output** — do
not hand-edit them. Edit the fragments under `common/` or the device
`.yaml.src` and re-run `build.py`.

## `build.py` flow

`build.py` is a small text-flattener. It has no ESPHome dependency
and does not compile or upload anything.

For each device template (`m5stickcplus/*.yaml.src`,
`m5sticks3/*.yaml.src`) it:

1. Reads the template line by line.
2. Replaces each `# !include <relative-path>` with the verbatim
   contents of the referenced fragment under `common/`.
3. Replaces each `# !include_variant <name>` with the contents of
   `common/variants/<variant>/<name>` where `<variant>` is `ha` or
   `standalone`.
4. Writes the flattened document to
   `dist/ghmonitorgizmo-{device}-{variant}.yaml`.

Re-run it whenever you edit any `common/*.yaml`, any device
`.yaml.src`, or any `common/variants/*/*.yaml`. The CI workflow runs
it on every push and fails if a second run produces a different
output (the build has to be idempotent).

```powershell
# Build all four outputs (two devices × two variants)
python build.py

# Build a single source to a custom path
python build.py m5stickcplus/ghmonitorgizmo.yaml.src `
    --variant standalone -o dist/foo.yaml
```

## Feature-gate pattern (substitutions)

Several optional features are toggled at **compile time** via ESPHome
[`substitutions:`][espsubs] at the top of the `.yaml.src` templates
— not at runtime. Examples currently in the tree:

- `dependabot_enabled` — include the Dependabot alert card + poller
- `beeps_enabled` — Plus 1.1 buzzer scripts (no-op on the S3)
- `card_beep_enabled` — per-card-flash beep during the idle loop
- `debug_mem_logs_enabled` — verbose heap logging
- `sleep_start_hour` / `sleep_end_hour` — night-mode window
- `idle_screen_off_cycles` / `idle_card_seconds` / `idle_bouncer_seconds`
  — idle behaviour

Each gate is consumed inside a fragment with either
`{% if dependabot_enabled == "true" %}` style templating (on a few
Jinja-processed fragments) or by splicing the substitution directly
into a `lambda:` guard. A disabled feature contributes **zero** code
to the flattened `dist/` output, which keeps the text segment small
enough to fit after OTA.

> **#9 migration note.** Some of these gates — notably the ones that
> make sense to flip without re-flashing (night-mode hours, idle
> timings, beep enables) — are on the migration path to runtime
> [`globals:`][espglobals] backed by HA `switch:` / `number:`
> entities. The structural gates that change which components are
> compiled in (e.g. `dependabot_enabled`, variant-level API choice)
> will stay as build-time substitutions. Track progress in [#9][i9].

## Dependabot REST integration

The Dependabot alert card uses
[`GET /user/dependabot/alerts`][gh-dep-rest] — a single REST call
that server-side aggregates every open alert the authenticated token
can see. We deliberately do **not** use the GraphQL
`vulnerabilityAlerts` fan-out; see
[crash-debug history](#crash-debug-history) for why.

### Token scope

A **classic PAT** with the **`repo`** scope is required. `repo` lets
the `/user/dependabot/alerts` endpoint enumerate alerts across every
repo the token can read.

> Do **not** use `security_events`. That scope is for the
> *per-repo* `/repos/{owner}/{repo}/dependabot/alerts` endpoint
> and does not satisfy the user-level aggregate endpoint we call.

### The 404-no-alerts quirk

When the authenticated user has **zero open Dependabot alerts** across
every reachable repo, GitHub returns **HTTP 404** instead of the
`[]` you might expect. The firmware treats this as a transient,
non-fatal state:

| Status           | Handling                                             |
|------------------|------------------------------------------------------|
| `200` + body     | Render severity tally                                |
| `404`            | Treat as "no alerts right now"; retry next interval  |
| `401` / `403`    | Disable the card until reboot (permission problem)  |
| Other            | Log + retry next interval                           |

Only `401` / `403` latch the card off; `404` does not — if an alert
appears later, the next 15-min poll will render it.

## Night-mode beep suppression

Night mode is a single global, `screen_asleep`, which is set true
between `sleep_start_hour` and `sleep_end_hour` (configurable
substitutions; defaults 20:00 → 08:00 local). While `screen_asleep`
is true:

- The backlight is off.
- The DVD bouncer and all non-events pollers are paused.
- **All beeps and card-beeps are short-circuited** in the
  corresponding `beep_*` scripts, so the device stays silent through
  the configured window even if a CI failure lands at 03:00.

Waking the screen (front button press, or an incoming event) does
not unsuppress beeps if the window is still active — the audio gate
keys off `screen_asleep`, which only flips back at
`sleep_end_hour`. This is intentional: bedroom-deployed units must
stay silent overnight.

Set `sleep_start_hour` equal to `sleep_end_hour` to disable night
mode entirely (beeps will then play at any hour).

## Crash-debug history

### S3 idle-task watchdog crash ([#2][i2], closed)

Early S3 builds deterministically crashed around uptime ~120 s with
an idle-task watchdog timeout. Root cause: the original Dependabot
integration used a GraphQL query that fanned out across up to 100
repositories' `vulnerabilityAlerts` connections. Under mbedTLS on
ESP-IDF that query pinned the main task inside TLS for >5 s every
900 s (plus on the startup delay), tripping the idle-task TWDT.

The fix, in commit [`61940a1`][c61940a1], was to replace the GraphQL
fan-out with the single-call REST endpoint
[`GET /user/dependabot/alerts`](#dependabot-rest-integration), which
server-aggregates and stays under an 8 KB response. The same commit
also wired per-fetch feature gates so that expensive fetchers can be
compiled out entirely on memory-constrained builds.

The S3 has been watchdog-stable since. See [#2][i2] for the full
thread.

## Hardware audits

Rolling hardware audits track which GPIO lines, power rails, and
peripherals are actually exercised by the firmware versus documented
by the manufacturer:

- **M5Stick S3 (K150)** — [#4][i4] (open)
- **M5StickC Plus 1.1** — [#7][i7] (open)

Both reference the authoritative manufacturer pages:

- [M5StickC Plus 1.1 docs][m5cplus]
- [M5Stick S3 docs][m5s3]

## See also

- [`../README.md`](../README.md) — user-facing quick start
- [`INSTALL-ha.md`](INSTALL-ha.md) — flashing via HA add-on
- [`INSTALL-standalone-web.md`](INSTALL-standalone-web.md) — flashing from Chrome/Edge
- [`INSTALL-standalone-cli.md`](INSTALL-standalone-cli.md) — classic `esphome run`

### Related issues

- [#2][i2] — Dependabot REST redesign (closed, see [crash-debug history](#crash-debug-history))
- [#4][i4] — M5Stick S3 hardware audit (open)
- [#7][i7] — M5StickC Plus 1.1 hardware audit (open)
- [#9][i9] — Community alignment / packages migration (open)
- [#10][i10] — BT-proxy variant (open)
- [#11][i11] — End-to-end validation (open)
- [#12][i12] — This documentation refresh

[espapi]: https://esphome.io/components/api
[espweb]: https://esphome.io/components/web_server
[espcp]: https://esphome.io/components/captive_portal
[espweb-flash]: https://web.esphome.io/
[espsubs]: https://esphome.io/guides/configuration-types.html#substitutions
[espglobals]: https://esphome.io/components/globals.html
[gh-dep-rest]: https://docs.github.com/en/rest/dependabot/alerts#list-dependabot-alerts-for-the-authenticated-user
[m5cplus]: https://docs.m5stack.com/en/core/m5stickc_plus
[m5s3]: https://docs.m5stack.com/en/core/StickS3
[c61940a1]: https://github.com/gjlumsden/gh-monitor-gizmo/commit/61940a1
[i2]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/2
[i4]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/4
[i7]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/7
[i9]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/9
[i10]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/10
[i11]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/11
[i12]: https://github.com/gjlumsden/gh-monitor-gizmo/issues/12
