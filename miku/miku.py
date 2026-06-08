#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import sys
import time
from pathlib import Path


ART_PATH = Path(__file__).with_name("text.md")
EMPTY = "\u2800"
FRAME_COUNT = 32
FRAME_DELAY = 1.0 / 16.0
SIGN_LINES = (
    "+--------+",
    "|  Skyy  |",
    "+---+----+",
    "    |",
)
EYE_ROWS = (18, 19, 20)
EYE_SPANS = ((24, 9), (42, 9))


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the Miku art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return EMPTY * offset + line
    if offset < 0:
        return line[-offset:] + EMPTY * min(-offset, 18)
    return line


def replace_span(chars: list[str], start: int, replacement: str) -> None:
    for index, char in enumerate(replacement):
        position = start + index
        if 0 <= position < len(chars):
            chars[position] = char


def blink_state(cycle_index: int) -> str:
    if cycle_index in (20, 24):
        return "half"
    if cycle_index in (21, 22, 23):
        return "closed"
    return "open"


def blink_art(art: list[str], cycle_index: int) -> list[str]:
    state = blink_state(cycle_index)
    if state == "open":
        return art

    lines = [list(line) for line in art]
    upper_row, lid_row, lower_row = EYE_ROWS
    lid_char = "_" if state == "half" else "-"

    for start, width in EYE_SPANS:
        replace_span(lines[upper_row], start, EMPTY * width)
        replace_span(lines[lid_row], start, lid_char * width)
        replace_span(lines[lower_row], start, EMPTY * width)

    return ["".join(line) for line in lines]


def append_skyy_sign(row: str, sign_index: int) -> str:
    if sign_index >= len(SIGN_LINES):
        return row
    return f"{row.rstrip(EMPTY)}   {SIGN_LINES[sign_index]}"


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = shutil.get_terminal_size(fallback=(120, 48))
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def render_frame(
    art: list[str],
    frame_number: int,
    *,
    cycle_count: int = FRAME_COUNT,
    sign: bool = True,
    crop: bool = False,
) -> str:
    cycle_index = (frame_number - 1) % cycle_count
    phase = 2.0 * math.pi * cycle_index / cycle_count
    axis_x = round(math.sin(phase) * 9.0)
    axis_y = round((math.cos(phase * 1.35) + 1.0) * 2.0)
    hair_sway = round(math.sin(phase * 2.0 + 0.25) * 1.5)
    base_indent = 9

    miku = blink_art(art, cycle_index)
    rows: list[str] = ["" for _ in range(axis_y)]
    center = len(miku) // 2
    show_sign = sign and cycle_index == 0

    for y, line in enumerate(miku):
        row_wave = round(math.sin(phase * 1.8 + y * 0.24) * 1.2)
        section_sway = hair_sway if y < center else -hair_sway
        offset = base_indent + axis_x + row_wave + section_sway
        row = move_line(line, offset)
        if show_sign and 2 <= y < 2 + len(SIGN_LINES):
            row = append_skyy_sign(row, y - 2)
        rows.append(row)

    sparkle_phase = math.sin(phase * 4.0)
    sparkle_indent = max(0, base_indent + axis_x + 35)
    if sparkle_phase > 0.65:
        rows.insert(0, f"{' ' * sparkle_indent}*")
    elif sparkle_phase < -0.65:
        rows.append(f"{' ' * max(0, sparkle_indent - 9)}*")

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(art: list[str], *, sign: bool, crop: bool) -> list[str]:
    return [
        render_frame(art, frame_number, sign=sign, crop=crop)
        for frame_number in range(1, FRAME_COUNT + 1)
    ]


def validate(art: list[str], frames: list[str]) -> None:
    if not art:
        raise ValueError("The source art has no lines.")
    if max(len(line) for line in art) == 0:
        raise ValueError("The source art has no visible width.")
    if len(frames) != FRAME_COUNT:
        raise ValueError(f"Expected {FRAME_COUNT} frames, got {len(frames)}.")
    if all(frame == frames[0] for frame in frames[1:]):
        raise ValueError("Generated frames are identical.")
    if "Skyy" not in frames[0]:
        raise ValueError("Frame 1 is missing the Skyy sign.")


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def animate(frames: list[str], delay: float) -> None:
    sys.stdout.write("\033[?25l")
    try:
        while True:
            for frame in frames:
                clear_screen()
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
    parser = argparse.ArgumentParser(description="Animate the Miku art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print the 32 frames once")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--no-sign", action="store_true", help="hide the Skyy sign on frame 1")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    art = load_art(args.source)
    frames = build_frames(art, sign=not args.no_sign, crop=args.crop)
    validate(art, frames)

    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0

    animate(frames, delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
