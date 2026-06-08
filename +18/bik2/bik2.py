#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import random
import shutil
import sys
import time
from pathlib import Path


ART_PATH = Path(__file__).with_name("text.md")
EMPTY = "\u2800"
FRAME_COUNT = 120
FRAME_DELAY = 1.0 / 20.0
MAX_SWAY_X = 4
MAX_FLOAT_Y = 2
SPARKLES = ("*", "+", ".")


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the bik2 art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(100, 44))


def position_limits(art: list[str]) -> tuple[int, int]:
    columns, lines = terminal_size()
    width = max(len(line) for line in art) + MAX_SWAY_X * 2
    height = len(art) + MAX_FLOAT_Y
    return max(0, columns - width - 1), max(0, lines - height - 1)


def pick_position(rng: random.Random, art: list[str]) -> tuple[int, int]:
    max_x, max_y = position_limits(art)
    return rng.randint(0, max_x), rng.randint(0, max_y)


def noise(x: int, y: int, frame_index: int) -> int:
    return (x * 43 + y * 61 + frame_index * 31) % 100


def visibility_for(cycle_index: int) -> float:
    phase = cycle_index / FRAME_COUNT
    if phase < 0.08 or phase >= 0.96:
        return 0.0
    if phase < 0.22:
        return (phase - 0.08) / 0.14
    if phase < 0.78:
        return 1.0
    return max(0.0, (0.96 - phase) / 0.18)


def glam_art(art: list[str], cycle_index: int, visibility: float) -> list[str]:
    if visibility <= 0.0:
        return [EMPTY * len(art[0]) for _ in art]

    shimmer = math.sin(cycle_index * 0.28)
    threshold = round(visibility * 100)
    rows: list[str] = []

    for y, line in enumerate(art):
        chars: list[str] = []
        for x, char in enumerate(line):
            if char == EMPTY or char == " ":
                chars.append(char)
                continue

            sparkle = noise(x, y, cycle_index)
            if sparkle >= threshold:
                chars.append(EMPTY)
            elif shimmer > 0.45 and (x + y + cycle_index) % 29 == 0:
                chars.append(SPARKLES[(x + y + cycle_index) % len(SPARKLES)])
            else:
                chars.append(char)
        rows.append("".join(chars))

    return rows


def has_visible_text(rows: list[str]) -> bool:
    return any(row.strip(EMPTY).strip() for row in rows)


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = terminal_size()
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def render_frame(
    art: list[str],
    frame_number: int,
    position: tuple[int, int],
    *,
    crop: bool = False,
) -> str:
    cycle_index = (frame_number - 1) % FRAME_COUNT
    phase = 2.0 * math.pi * cycle_index / FRAME_COUNT
    visibility = visibility_for(cycle_index)
    rows = glam_art(art, cycle_index, visibility)

    if not has_visible_text(rows):
        return ""

    base_x, base_y = position
    sway_x = round(math.sin(phase) * MAX_SWAY_X)
    float_y = round((math.cos(phase * 1.4) + 1.0) * MAX_FLOAT_Y / 2.0)
    rendered: list[str] = ["" for _ in range(base_y + float_y)]

    for y, line in enumerate(rows):
        row_wave = round(math.sin(phase * 2.0 + y * 0.24) * 1.0)
        indent = max(0, base_x + MAX_SWAY_X + sway_x + row_wave)
        rendered.append(" " * indent + line.rstrip(EMPTY))

    if crop:
        rendered = crop_to_terminal(rendered)
    return "\n".join(rendered)


def build_frames(art: list[str], rng: random.Random, *, crop: bool) -> list[str]:
    position = pick_position(rng, art)
    return [
        render_frame(art, frame_number, position, crop=crop)
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
    if not any(frame == "" for frame in frames):
        raise ValueError("The animation never fully fades out.")
    if not any(frame.strip(EMPTY).strip() for frame in frames):
        raise ValueError("The animation never appears.")


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def animate(art: list[str], rng: random.Random, *, delay: float, crop: bool) -> None:
    sys.stdout.write("\033[?25l")
    try:
        while True:
            position = pick_position(rng, art)
            for frame_number in range(1, FRAME_COUNT + 1):
                clear_screen()
                frame = render_frame(art, frame_number, position, crop=crop)
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
    parser = argparse.ArgumentParser(description="Animate the bik2 art with a glam shimmer effect.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print one 120-frame cycle")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--seed", type=int, help="use repeatable random positions")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    rng = random.Random(args.seed)
    art = load_art(args.source)
    frames = build_frames(art, rng, crop=args.crop)
    validate(art, frames)

    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0

    animate(art, rng, delay=delay, crop=args.crop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
