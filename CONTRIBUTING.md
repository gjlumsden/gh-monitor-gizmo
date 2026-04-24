# Contributing to gh-monitor-gizmo

Thanks for your interest. This guide is for people editing the
firmware, not for people flashing it — if you just want to install a
pre-built YAML, start at the [README](README.md).

For the runtime design (feature gates, Dependabot REST integration,
night-mode, crash history) see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository layout

```
m5stickcplus/ghmonitorgizmo.yaml.src        Plus 1.1 device template
m5sticks3/ghmonitorgizmo-s3.yaml.src        S3 device template
common/*.yaml                               Shared fragments (display,
                                            scripts, globals, sensors…)
common/variants/<variant>/api.yaml          Per-variant integration
                                            layer (ha, standalone,
                                            ha-btproxy)
build.py                                    Text-level # !include
                                            resolver (see below)
dist/                                       Generated output
                                            (git-ignored)
secrets.yaml                                Your local secrets
                                            (git-ignored)
```

You **edit** `common/*.yaml` and the two `*.yaml.src` device
templates. You do **not** hand-edit anything under `dist/` — it is
regenerated from source.

## Why `# !include` instead of native ESPHome `packages:`

`common/display_lambda.yaml` is a **C++ lambda body fragment**, not a
YAML document. ESPHome's native [`packages:`][esppackages] component
composes at the YAML tree level, so it cannot include a lambda body
from a separate file. Until the display is refactored into an external
C++ component (tracked on
[issue #9](https://github.com/gjlumsden/gh-monitor-gizmo/issues/9)),
the build pipeline uses a tiny text-level preprocessor
([`build.py`](build.py)) that inlines `# !include <path>` markers
verbatim.

This means the `dist/` YAMLs are **fully self-contained**: they paste
cleanly into the Home Assistant ESPHome add-on, into
[web.esphome.io][espweb-flash], or into a local `esphome compile`, with
no `packages:` resolution at flash time.

[esppackages]: https://esphome.io/components/packages
[espweb-flash]: https://web.esphome.io/

## Build workflow

From the repo root:

```powershell
python build.py
```

That regenerates every file under `dist/`. The script has zero
dependencies beyond the Python standard library — no ESPHome install
required.

To build a single source to a custom path:

```powershell
python build.py m5stickcplus/ghmonitorgizmo.yaml.src `
    --variant standalone -o dist/foo.yaml
```

`python build.py` must be **idempotent**: a second run must produce
byte-identical `dist/` output. CI enforces this on every push and
pull request (see [`.github/workflows/build.yml`](.github/workflows/build.yml)).

### Variant matrix

Running `python build.py` produces **five** files — one per row
below. The BT proxy variant is S3-only because the M5StickC Plus 1.1
ships with `CONFIG_BT_ENABLED: n` in this firmware (the AXP192 + ESP32
combination has no headroom for Bluetooth alongside everything else).

| Device             | Variant       | Output                                      |
|--------------------|---------------|---------------------------------------------|
| M5StickC Plus 1.1  | `ha`          | `dist/ghmonitorgizmo-cplus-ha.yaml`         |
| M5StickC Plus 1.1  | `standalone`  | `dist/ghmonitorgizmo-cplus-standalone.yaml` |
| M5Stick S3 (K150)  | `ha`          | `dist/ghmonitorgizmo-s3-ha.yaml`            |
| M5Stick S3 (K150)  | `standalone`  | `dist/ghmonitorgizmo-s3-standalone.yaml`    |
| M5Stick S3 (K150)  | `ha-btproxy`  | `dist/ghmonitorgizmo-s3-ha-btproxy.yaml`    |

The canonical source-of-truth is the `DEVICES` list at the top of
[`build.py`](build.py); the CI sanity check counts entries in that
list, so adding or removing a row there is the only edit required.

## Secrets handling

Every `dist/*.yaml` uses ESPHome's `!secret` references. It is
**your** responsibility to supply a `secrets.yaml` with the right keys
wherever you run `esphome compile` from (or paste the YAML into the
Home Assistant ESPHome add-on, which has its own secrets store).

- Start from [`secrets.yaml.example`](secrets.yaml.example).
- Never commit a populated `secrets.yaml`; it is git-ignored at both
  the repo root and under `m5sticks3/`.
- `build.py` does **not** copy `secrets.yaml` into `dist/`. If you
  want one there for local `esphome compile`, drop it in manually —
  it will be ignored by git.

## Adding a new shared fragment

1. Create the file under `common/` (e.g. `common/my_feature.yaml`).
2. Add `# !include my_feature.yaml` at the right spot in each device
   `*.yaml.src` that should get it. The marker is replaced verbatim,
   so place it at the indentation level the fragment already uses —
   `build.py` does no re-indentation.
3. Run `python build.py` and inspect the diff in `dist/`.

## Adding a new variant

Variants swap the integration layer under `common/variants/<variant>/`
(currently `ha/`, `standalone/`, `ha-btproxy/`). To add one:

1. Create `common/variants/<variant>/api.yaml` (plus any other
   variant-specific fragments).
2. Add the corresponding `--variant` choice to the CLI parser in
   [`build.py`](build.py).
3. Add an entry to the `DEVICES` list in `build.py` pointing at the
   new output path.
4. Run `python build.py`. CI's sanity check is data-driven off
   `DEVICES`, so it will accept the new file automatically.
5. Update the variant matrix above and the one in the
   [README](README.md#download-the-firmware-yaml).

## Adding a new device

This is a larger change because it adds a new `*.yaml.src` template.
Start by reading how the existing two device templates compose
`common/*` fragments, then:

1. Add `mynewdevice/ghmonitorgizmo-xxx.yaml.src`.
2. Add one `DEVICES` entry per variant you support.
3. Update [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the README
   variant matrix.

## Pull request workflow

1. Run `python build.py` before committing. Your PR must leave `dist/`
   consistent with `common/` and the `.yaml.src` templates.
2. CI will run `python build.py` twice and fail the PR if the second
   run produces a different `dist/`. This catches non-determinism
   (e.g. dict-iteration order leaking into output).
3. Include a one-line description of what `dist/` changes shipped in
   the PR body, even if they're mechanical — it saves reviewers a
   regeneration step.

## Deferred: native `packages:` migration

Issue #9 parts A (native packages) and B (thin `build.py`) are on
hold pending a design decision on how to compose the display lambda
from `common/display_lambda.yaml`. Options under consideration:

- Extract the lambda body into an external C++ component. Biggest
  refactor; unblocks full native packages.
- Split the lambda into many small `lambda:` actions composed in
  YAML. Large refactor; likely hurts readability.
- Keep the text-level includes for the display only, migrate
  everything else to native packages. Hybrid; limited win.

Input on this welcome — comment on
[issue #9](https://github.com/gjlumsden/gh-monitor-gizmo/issues/9).

## Questions

Open an issue or a draft PR. For hardware-specific quirks also see
the audits in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#hardware-audits).
