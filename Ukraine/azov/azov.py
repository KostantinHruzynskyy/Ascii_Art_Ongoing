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
FRAME_COUNT = 110
FRAME_DELAY = 1.0 / 20.0
STREAM_WIDTH = 18
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
        raise SystemExit(f"Could not find {path}. Put the L art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return EMPTY * offset + line
    if offset < 0:
        return line[-offset:] + EMPTY * min(-offset, 14)
    return line


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(128, 42))


def noise(x: int, y: int, frame_index: int) -> int:
    return (x * 37 + y * 53 + frame_index * 29) % 100


def stream_visibility(cycle_index: int, x: int, y: int, width: int) -> float:
    wave_x = x + math.sin(y * 0.42 + cycle_index * 0.25) * 4.0

    if cycle_index < 6:
        return 0.0

    if cycle_index < 36:
        progress = (cycle_index - 6) / 30.0
        head = progress * (width + STREAM_WIDTH) - STREAM_WIDTH
        if wave_x < head - STREAM_WIDTH:
            return 1.0
        if wave_x < head:
            return 0.78
        if wave_x < head + STREAM_WIDTH:
            return 0.32
        return 0.0

    if cycle_index < 76:
        ripple = math.sin(cycle_index * 0.45 + y * 0.55 + x * 0.12)
        return 0.72 if ripple > 0.72 else 1.0

    if cycle_index < 104:
        progress = (cycle_index - 76) / 28.0
        head = progress * (width + STREAM_WIDTH) - STREAM_WIDTH
        if wave_x < head - STREAM_WIDTH:
            return 0.0
        if wave_x < head:
            return 0.28
        if wave_x < head + STREAM_WIDTH:
            return 0.62
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


def render_frame(art: list[str], frame_number: int, *, crop: bool = False) -> str:
    cycle_index = (frame_number - 1) % FRAME_COUNT
    phase = 2.0 * math.pi * cycle_index / FRAME_COUNT
    axis_x = round(math.sin(phase) * 7.0)
    axis_y = round((math.cos(phase * 1.25) + 1.0) * 2.0)
    base_indent = 5

    streamed = flowstream_art(art, cycle_index)
    show_sign = frame_number in SIGN_FRAMES
    if not show_sign and not any(line.strip(EMPTY).strip() for line in streamed):
        return ""

    rows: list[str] = ["" for _ in range(axis_y)]
    for y, line in enumerate(streamed):
        row_wave = round(math.sin(phase * 1.8 + y * 0.18) * 1.0)
        offset = base_indent + axis_x + row_wave
        row = move_line(line.rstrip(EMPTY), offset)
        if show_sign and 2 <= y < 2 + len(SIGN_LINES):
            row = append_skyy_sign(row, y - 2)
        rows.append(row)

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(art: list[str], *, crop: bool) -> list[str]:
    return [render_frame(art, frame_number, crop=crop) for frame_number in range(1, FRAME_COUNT + 1)]


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
    parser = argparse.ArgumentParser(description="Animate the L art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print one 110-frame cycle")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    art = load_art(args.source)
    frames = build_frames(art, crop=args.crop)
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
