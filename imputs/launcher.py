#!/usr/bin/env python3
"""
ASCII Art Visualization Launcher
Choose from multiple visualization modes for ASCII art in text.md
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sys
from pathlib import Path


ART_PATH = Path(__file__).parent / "text.md"
MODES = {
    "cascade": "Cascade - wave-like horizontal movement",
    "shadow": "Shadow - animated shadow effect",
    "blink": "Blink - random blinking/sparkle effect",
    "wave": "Wave - smooth wave motion",
    "pulse": "Pulse - radial pulse from center",
    "glitch": "Glitch - digital glitch effects",
    "zoom": "Zoom - pulsing zoom in/out",
    "spiral": "Spiral - rotating spiral pattern",
    "ripple": "Ripple - concentric ripple waves",
    "matrix": "Matrix - digital matrix rain effect",
    "fire": "Fire - flickering fire effect",
}


def list_sections(source: Path) -> list[str]:
    try:
        text = source.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return []

    sections: list[str] = []
    current_name = "DEFAULT"
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and all(c == stripped[0] for c in stripped) and len(stripped) > 3:
            if current_lines:
                sections.append(current_name)
            current_name = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(current_name)

    return sections


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ASCII Art Visualization Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available modes:
{chr(10).join(f"  {name:12} - {desc}" for name, desc in MODES.items())}

Examples:
  python launcher.py cascade              # Run cascade mode
  python launcher.py blink --section SKULL # Run blink on SKULL section
  python launcher.py wave --once          # Print wave frames once
  python launcher.py --list-sections      # List available art sections
""",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=list(MODES.keys()),
        help="visualization mode to run",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=ART_PATH,
        help="art file to animate (default: imputs/text.md)",
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="list available art sections in the source file",
    )
    parser.add_argument(
        "--list-modes",
        action="store_true",
        help="list available visualization modes",
    )
    parser.add_argument(
        "mode_args",
        nargs=argparse.REMAINDER,
        help="arguments to pass to the selected mode",
    )

    args = parser.parse_args(argv)

    if args.list_modes:
        print("Available visualization modes:\n")
        for name, desc in MODES.items():
            print(f"  {name:12} - {desc}")
        return 0

    if args.list_sections:
        sections = list_sections(args.source)
        if sections:
            print(f"Sections in {args.source}:\n")
            for section in sections:
                print(f"  {section}")
        else:
            print(f"No sections found in {args.source}")
        return 0

    if not args.mode:
        parser.print_help()
        return 1

    # Import and run the selected mode
    mode_path = Path(__file__).parent / f"{args.mode}.py"
    spec = importlib.util.spec_from_file_location(args.mode, mode_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Build argv for the mode's main function
    mode_argv = args.mode_args
    if args.source != ART_PATH:
        # Insert --source before other args if it's not default
        mode_argv = ["--source", str(args.source)] + mode_argv

    return module.main(mode_argv)


if __name__ == "__main__":
    raise SystemExit(main())