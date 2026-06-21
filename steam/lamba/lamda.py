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
FRAME_COUNT = 110
FRAME_DELAY = 1.0 / 20.0
STREAM_WIDTH = 14
MAX_AXIS_X = 7
MAX_AXIS_Y = 4
SIGN_FRAMES = {20, 60, 100}
SIGN_LINES = (
    "+--------+",
    "|  Skyy  |",
    "+---+----+",
    "    |",
)


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the joker5 art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return EMPTY * offset + line
    if offset < 0:
        return line[-offset:] + EMPTY * min(-offset, 12)
    return line


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(110, 46))


def frame_position_limit(art: list[str]) -> tuple[int, int]:
    columns, lines = terminal_size()
    art_width = max(len(line) for line in art)
    art_height = len(art)
    sign_width = max(len(line) for line in SIGN_LINES) + 3
    draw_width = art_width + sign_width + (MAX_AXIS_X * 2)
    draw_height = art_height + MAX_AXIS_Y
    max_x = max(0, columns - draw_width - 1)
    max_y = max(0, lines - draw_height - 1)
    return max_x, max_y


def pick_position(rng: random.Random, art: list[str]) -> tuple[int, int]:
    max_x, max_y = frame_position_limit(art)
    return rng.randint(0, max_x), rng.randint(0, max_y)


def noise(x: int, y: int, frame_index: int) -> int:
    return (x * 41 + y * 59 + frame_index * 31) % 100


def stream_visibility(cycle_index: int, x: int, y: int, width: int) -> float:
    wave_x = x + math.sin(y * 0.38 + cycle_index * 0.22) * 3.5

    if cycle_index < 6:
        return 0.0

    if cycle_index < 36:
        progress = (cycle_index - 6) / 30.0
        head = progress * (width + STREAM_WIDTH) - STREAM_WIDTH
        if wave_x < head - STREAM_WIDTH:
            return 1.0
        if wave_x < head:
            return 0.8
        if wave_x < head + STREAM_WIDTH:
            return 0.34
        return 0.0

    if cycle_index < 76:
        ripple = math.sin(cycle_index * 0.43 + y * 0.5 + x * 0.14)
        return 0.68 if ripple > 0.7 else 1.0

    if cycle_index < 104:
        progress = (cycle_index - 76) / 28.0
        head = progress * (width + STREAM_WIDTH) - STREAM_WIDTH
        if wave_x < head - STREAM_WIDTH:
            return 0.0
        if wave_x < head:
            return 0.26
        if wave_x < head + STREAM_WIDTH:
            return 0.6
        return 1.0

    return 0.0


def flowstream_art(art: list[str], cycle_index: int) -> list[str]:
    width = max(len(line) for line in art)
    streamed: list[str] = []

    for y, line in enumerate(art):
        chars: list[str] = []
        for x, char in enumerate(line):
            if char == EMPTY or char == " ":
                chars.append(char)
                continue

            visibility = stream_visibility(cycle_index, x, y, width)
            if visibility >= 1.0:
                chars.append(char)
            elif visibility <= 0.0:
                chars.append(EMPTY)
            else:
                chars.append(char if noise(x, y, cycle_index) < visibility * 100 else EMPTY)
        streamed.append("".join(chars))

    return streamed


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = terminal_size()
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def append_skyy_sign(row: str, sign_index: int) -> str:
    if sign_index >= len(SIGN_LINES):
        return row
    return f"{row.rstrip(EMPTY)}   {SIGN_LINES[sign_index]}"


def render_frame(
    art: list[str],
    frame_number: int,
    position: tuple[int, int],
    *,
    crop: bool = False,
) -> str:
    cycle_index = (frame_number - 1) % FRAME_COUNT
    phase = 2.0 * math.pi * cycle_index / FRAME_COUNT
    axis_x = round(math.sin(phase) * 6.0)
    axis_y = round((math.cos(phase * 1.2) + 1.0) * 2.0)
    base_x, base_y = position

    streamed = flowstream_art(art, cycle_index)
    show_sign = frame_number in SIGN_FRAMES
    if not show_sign and not any(line.strip(EMPTY).strip() for line in streamed):
        return ""

    rows: list[str] = ["" for _ in range(base_y + axis_y)]
    for y, line in enumerate(streamed):
        row_wave = round(math.sin(phase * 1.7 + y * 0.2) * 1.0)
        offset = base_x + MAX_AXIS_X + axis_x + row_wave
        row = move_line(line.rstrip(EMPTY), offset)
        if show_sign and 2 <= y < 2 + len(SIGN_LINES):
            row = append_skyy_sign(row, y - 2)
        rows.append(row)

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


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
        raise ValueError("The flowstream never fully disappears.")
    if not any(frame.strip() for frame in frames):
        raise ValueError("The flowstream never appears.")
    for frame_number in SIGN_FRAMES:
        if "Skyy" not in frames[frame_number - 1]:
            raise ValueError(f"Frame {frame_number} is missing the Skyy sign.")


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
    parser = argparse.ArgumentParser(description="Animate the joker5 art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print one 110-frame cycle")
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
