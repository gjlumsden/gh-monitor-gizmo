#!/usr/bin/env python3
"""Inline `# !include` markers to produce self-contained ESPHome YAML.

Each source template (``*.yaml.src``) is read line by line. Any line matching
``# !include <path>`` is replaced verbatim by the contents of the referenced
file (path is resolved relative to the including file). Inclusion is
recursive; cycles are detected and rejected.

No re-indentation is performed: each common fragment is stored at the exact
indentation level it will appear in the final output, so the ``# !include``
marker must sit at column 0 (or wherever the fragment's existing indent
expects to slot in).

Usage
-----
    python build.py                           # build all known devices
    python build.py path/to/device.yaml.src   # build a single source
    python build.py <src> -o dist/out.yaml    # override output path

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

DEVICES: list[tuple[str, str]] = [
    ("m5stickcplus/ghmonitorgizmo.yaml.src", "dist/ghmonitorgizmo-cplus.yaml"),
    ("m5sticks3/ghmonitorgizmo-s3.yaml.src", "dist/ghmonitorgizmo-s3.yaml"),
]


def resolve(src: Path, seen: frozenset[Path] | None = None) -> str:
    seen = seen or frozenset()
    rp = src.resolve()
    if rp in seen:
        raise RuntimeError(f"include cycle detected at {rp}")
    if not src.is_file():
        raise FileNotFoundError(f"include target not found: {src}")
    seen = seen | {rp}

    out: list[str] = []
    for raw in src.read_text(encoding="utf-8").splitlines():
        m = INCLUDE_RE.match(raw)
        if not m:
            out.append(raw)
            continue
        target = (src.parent / m.group(1)).resolve()
        included = resolve(target, seen)
        # Preserve trailing blank lines: splitlines('a\n\n') -> ['a', ''],
        # which when re-joined retains the blank. Stripping the final '\n'
        # would collapse it and swallow separator blanks between blocks.
        out.extend(included.splitlines())
    return "\n".join(out) + "\n"


def build(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    content = resolve(src)
    # Sanity check: no stray include markers must remain
    for i, ln in enumerate(content.splitlines(), 1):
        if INCLUDE_RE.match(ln):
            raise RuntimeError(f"unresolved include at {dst}:{i}: {ln!r}")
    dst.write_text(content, encoding="utf-8", newline="\n")
    print(f"built {dst} ({len(content.splitlines())} lines)")


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
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parent

    if args.source:
        src = Path(args.source).resolve()
        if args.output:
            dst = Path(args.output).resolve()
        else:
            # Default: dist/<stem-without-.yaml>.yaml
            stem = src.name
            if stem.endswith(".yaml.src"):
                stem = stem[: -len(".yaml.src")] + ".yaml"
            elif stem.endswith(".src"):
                stem = stem[: -len(".src")]
            dst = root / "dist" / stem
        build(src, dst)
    else:
        for s, d in DEVICES:
            build(root / s, root / d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
