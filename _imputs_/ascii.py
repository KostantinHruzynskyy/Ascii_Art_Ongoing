#!/usr/bin/env python3
"""
ASCII mode - displays art using only standard ASCII characters,
no Unicode block elements or special characters.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ART_PATH = Path(__file__).parent / "text.md"
EMPTY = " "
ASCII_CHARS = " .:-=+*#%@"

def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}.") from error
    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")
    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]

def parse_art_sections(art_lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_name = "DEFAULT"
    current_lines: list[str] = []
    for line in art_lines:
        stripped = line.strip()
        if stripped and all(c == stripped[0] for c in stripped) and len(stripped) > 3:
            if current_lines:
                sections[current_name] = current_lines
            current_name = stripped
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections[current_name] = current_lines
    return sections

def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(100, 40))

def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = terminal_size()
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows

def render_ascii_frame(art: list[str], frame_number: int, *, crop: bool = False) -> str:
    rows: list[str] = []
    for line in art:
        chars: list[str] = []
        for char in line:
            if char == EMPTY or char == " ":
                chars.append(EMPTY)
            elif char in "█▓▒░":
                # Map Unicode blocks to ASCII
                idx = "█▓▒░".index(char)
                chars.append(ASCII_CHARS[min(idx + 2, len(ASCII_CHARS) - 1)])
            else:
                # Keep standard ASCII characters
                if ord(char) < 128:
                    chars.append(char)
                else:
                    # Replace non-ASCII with closest ASCII equivalent
                    chars.append("#")
        rows.append("".join(chars))
    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)

def build_frames(art: list[str], *, crop: bool) -> list[str]:
    return [render_ascii_frame(art, 1, crop=crop)]

def validate(art: list[str], frames: list[str]) -> None:
    if not art:
        raise ValueError("The source art has no lines.")
    if max(len(line) for line in art) == 0:
        raise ValueError("The source art has no visible width.")
    if not frames:
        raise ValueError("No frames generated.")

def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")

def animate(art: list[str], delay: float, crop: bool) -> None:
    sys.stdout.write("\033[?25l")
    try:
        while True:
            clear_screen()
            frame = render_ascii_frame(art, 1, crop=crop)
            sys.stdout.write(frame)
            sys.stdout.flush()
            time.sleep(delay)
    except KeyboardInterrupt:
        clear_screen()
    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()

def print_frames(frames: list[str]) -> None:
    for index, frame in enumerate(frames, start=1):
        print(f"FRAME {index:03d}")
        print(frame)
        if index != len(frames):
            print()

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ASCII visualization mode.")
    parser.add_argument("delay", nargs="?", type=float, default=1.0)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print frames once")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--crop", action="store_true", help="crop frames to terminal size")
    parser.add_argument("--section", type=str, default=None, help="art section to use")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    delay = max(0.01, args.delay)
    raw_art = load_art(args.source)
    sections = parse_art_sections(raw_art)
    if args.section:
        section_name = args.section.upper()
        if section_name not in sections:
            raise SystemExit(f"Section '{section_name}' not found. Available: {list(sections.keys())}")
        art = sections[section_name]
    else:
        art = raw_art
    frames = build_frames(art, crop=args.crop)
    validate(art, frames)
    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0
    animate(art, delay, crop=args.crop)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())