#!/usr/bin/env python3
"""Inline `# !include` markers to produce self-contained ESPHome YAML.

Each source template (``*.yaml.src``) is read line by line. Two marker
directives are supported:

* ``# !include <path>`` - replaced verbatim by the contents of the
  referenced file. Paths are resolved relative to the including file.
* ``# !include_variant <name>`` - replaced by the contents of
  ``common/variants/<variant>/<name>`` where ``<variant>`` is supplied
  by the per-device build entry. Used to swap the integration layer
  (Home Assistant ``api:`` vs standalone ``web_server:``) without
  duplicating the hardware template.

Inclusion is recursive; cycles are detected and rejected. No
re-indentation is performed: each fragment is stored at the exact
indentation level it will appear in the final output, so markers must
sit at column 0 (or wherever the fragment's existing indent expects to
slot in).

Usage
-----
    python build.py                           # build all known devices
    python build.py path/to/device.yaml.src --variant ha -o out.yaml

Outputs land in ``dist/`` by default. Run ``esphome compile dist/<name>.yaml``
after building to compile locally, or upload the same file through the Home
Assistant ESPHome add-on for install.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INCLUDE_RE = re.compile(r"^\s*#\s*!include\s+(\S+)\s*$")
INCLUDE_VARIANT_RE = re.compile(r"^\s*#\s*!include_variant\s+(\S+)\s*$")

# (source template, output path, variant name). The variant name is
# resolved to ``common/variants/<variant>/<name>`` at build time.
DEVICES: list[tuple[str, str, str]] = [
    ("m5stickcplus/ghmonitorgizmo.yaml.src", "dist/ghmonitorgizmo-cplus-ha.yaml",         "ha"),
    ("m5stickcplus/ghmonitorgizmo.yaml.src", "dist/ghmonitorgizmo-cplus-standalone.yaml", "standalone"),
    ("m5sticks3/ghmonitorgizmo-s3.yaml.src", "dist/ghmonitorgizmo-s3-ha.yaml",            "ha"),
    ("m5sticks3/ghmonitorgizmo-s3.yaml.src", "dist/ghmonitorgizmo-s3-standalone.yaml",    "standalone"),
]


def resolve(src: Path, variant: str, root: Path, seen: frozenset[Path] | None = None) -> str:
    seen = seen or frozenset()
    rp = src.resolve()
    if rp in seen:
        raise RuntimeError(f"include cycle detected at {rp}")
    if not src.is_file():
        raise FileNotFoundError(f"include target not found: {src}")
    seen = seen | {rp}

    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        m = INCLUDE_VARIANT_RE.match(raw)
        if m:
            target = (root / "common" / "variants" / variant / m.group(1)).resolve()
            out.extend(resolve(target, variant, root, seen).splitlines())
            continue
        m = INCLUDE_RE.match(raw)
        if m:
            target = (src.parent / m.group(1)).resolve()
            out.extend(resolve(target, variant, root, seen).splitlines())
            continue
        out.append(raw)
    # Preserve trailing blank lines: splitlines('a\n\n') -> ['a', ''],
    # which when re-joined retains the blank. Stripping the final '\n'
    # would collapse it and swallow separator blanks between blocks.
    return "\n".join(out) + "\n"


def build(src: Path, dst: Path, variant: str, root: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = resolve(src, variant, root)
    # Sanity check: no stray include markers must remain
    for i, ln in enumerate(content.splitlines(), 1):
        if INCLUDE_RE.match(ln) or INCLUDE_VARIANT_RE.match(ln):
            raise RuntimeError(f"unresolved include at {dst}:{i}: {ln!r}")
    dst.write_text(content, encoding="utf-8", newline="\n")
    print(f"built {dst} ({len(content.splitlines())} lines, variant={variant})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "source",
        nargs="?",
        help="single source .yaml.src to build (default: all known devices)",
    )
    ap.add_argument(
        "-o",
        "--output",
        help="output path (only meaningful when a single source is given)",
    )
    ap.add_argument(
        "--variant",
        default="ha",
        choices=["ha", "standalone"],
        help="variant to build when a single source is given (default: ha)",
    )
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent

    if args.source:
        src = Path(args.source).resolve()
        if args.output:
            dst = Path(args.output).resolve()
        else:
            # Default: dist/<stem-without-.yaml>-<variant>.yaml
            stem = src.name
            if stem.endswith(".yaml.src"):
                stem = stem[: -len(".yaml.src")] + f"-{args.variant}.yaml"
            elif stem.endswith(".src"):
                stem = stem[: -len(".src")]
            dst = root / "dist" / stem
        build(src, dst, args.variant, root)
    else:
        for s, d, v in DEVICES:
            build(root / s, root / d, v, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
