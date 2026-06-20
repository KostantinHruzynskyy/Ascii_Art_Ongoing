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
FILL = "\u2800"
FRAME_COUNT = 80
FRAME_DELAY = 1.0 / 24.0
CAPTIONS = ("ATOMIC SKULL", "CORE ONLINE", "CRITICAL SMILE", "ATOMIC SKULL")


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the atomic skull art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, FILL) for line in lines]


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return FILL * offset + line
    if offset < 0:
        return line[-offset:] + FILL * min(-offset, 14)
    return line


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = shutil.get_terminal_size(fallback=(100, 40))
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def paint(rows: list[str], x: int, y: int, char: str) -> None:
    if y < 0 or y >= len(rows) or x < 0:
        return
    width = max(len(row) for row in rows)
    if x >= width:
        return
    chars = list(rows[y].ljust(width, FILL))
    chars[x] = char
    rows[y] = "".join(chars)


def caption_for(frame_number: int) -> str:
    return CAPTIONS[((frame_number - 1) // 20) % len(CAPTIONS)]


def render_frame(
    art: list[str],
    frame_number: int,
    *,
    caption: bool = True,
    crop: bool = False,
) -> str:
    phase = 2.0 * math.pi * ((frame_number - 1) % FRAME_COUNT) / FRAME_COUNT
    beat = math.sin(phase * 3.0)
    float_y = round((math.sin(phase * 2.0) + 1.0) * 2.0)
    launch_sway = round(math.sin(phase) * 9.0)
    skull_roll = round(math.sin(phase * 2.7 + 0.4) * 3.0)
    jaw_kick = round(math.sin(phase * 7.0) * 2.0)
    base_indent = 12

    rows = [FILL * (len(art[0]) + base_indent + 30) for _ in range(float_y)]
    center_y = len(art) / 2.0

    for y, line in enumerate(art):
        row_wave = round(math.sin(phase * 2.2 + y * 0.75) * 2.0)
        section = skull_roll if y < center_y else -skull_roll + jaw_kick
        offset = base_indent + launch_sway + section + row_wave
        rows.append(move_line(line, offset))

    core_x = base_indent + 15 + launch_sway
    core_y = float_y + 7
    particles = ("*", "o", "+", ".", "*", "o", "+", ".")
    for index, char in enumerate(particles):
        angle = phase * 2.4 + index * math.tau / len(particles)
        radius_x = 24 + round(math.sin(phase * 1.5 + index) * 3)
        radius_y = 8 + round(math.cos(phase * 1.2 + index) * 2)
        x = core_x + round(math.cos(angle) * radius_x)
        y = core_y + round(math.sin(angle) * radius_y)
        paint(rows, x, y, char)

    for spark in range(5):
        x = core_x + round(math.sin(phase * (spark + 3) + spark) * 34)
        y = core_y + round(math.cos(phase * (spark + 2) - spark) * 10)
        paint(rows, x, y, "." if spark % 2 else "+")

    if caption:
        pulse = ">" if beat >= 0 else "<"
        label = caption_for(frame_number)
        indent = max(0, base_indent + launch_sway + 3)
        rows.extend(("", f"{' ' * indent}{pulse} {label} {pulse}"))

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(art: list[str], count: int, *, caption: bool, crop: bool) -> list[str]:
    return [
        render_frame(art, frame_number, caption=caption, crop=crop)
        for frame_number in range(1, count + 1)
    ]


def validate(art: list[str], frames: list[str]) -> None:
    if not art:
        raise ValueError("The source art has no lines.")
    if max(len(line) for line in art) == 0:
        raise ValueError("The source art has no visible width.")
    if len(frames) < 2:
        raise ValueError("Need at least two frames to animate.")
    if all(frame == frames[0] for frame in frames[1:]):
        raise ValueError("Generated frames are identical.")


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
    parser = argparse.ArgumentParser(description="Animate the atomic skull art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--frames", type=int, default=FRAME_COUNT, help="number of animation frames")
    parser.add_argument("--once", action="store_true", help="print the generated frames once")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--no-caption", action="store_true", help="hide the title caption")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    frame_count = max(2, args.frames)
    art = load_art(args.source)
    frames = build_frames(art, frame_count, caption=not args.no_caption, crop=args.crop)
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
