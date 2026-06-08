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
FRAME_COUNT = 200
SLOT_COUNT = 4
SLOT_LENGTH = FRAME_COUNT // SLOT_COUNT
FRAME_DELAY = 1.0 / 20.0
FALL_HEIGHT = 9
SIGN_LINES = (
    "+--------+",
    "|  Skyy  |",
    "+---+----+",
    "    |",
)
EYE_ROWS = (16, 17, 18)
EYE_SPANS = ((14, 3), (18, 3))


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the Sk art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(100, 48))


def noise(x: int, y: int, frame_index: int) -> int:
    return (x * 47 + y * 67 + frame_index * 31) % 100


def replace_span(chars: list[str], start: int, replacement: str) -> None:
    for index, char in enumerate(replacement):
        position = start + index
        if 0 <= position < len(chars):
            chars[position] = char


def blink_state(slot_phase: int) -> str:
    if slot_phase in (23, 29, 36):
        return "half"
    if slot_phase in (24, 25, 26, 27, 28, 37, 38):
        return "closed"
    return "open"


def blink_art(art: list[str], slot_phase: int) -> list[str]:
    state = blink_state(slot_phase)
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


def waterfall_visibility(slot_phase: int, x: int, y: int, height: int) -> float:
    wave_y = y + math.sin(x * 0.38 + slot_phase * 0.55) * 2.0

    if slot_phase <= 3 or slot_phase >= 48:
        return 0.0

    if slot_phase < 17:
        progress = (slot_phase - 4) / 13.0
        head = progress * (height + FALL_HEIGHT) - FALL_HEIGHT
        if wave_y < head - FALL_HEIGHT:
            return 1.0
        if wave_y < head:
            return 0.72
        if wave_y < head + FALL_HEIGHT:
            return 0.28
        return 0.0

    if slot_phase < 35:
        ripple = math.sin(slot_phase * 0.8 + x * 0.33 + y * 0.22)
        return 0.68 if ripple > 0.78 else 1.0

    progress = (slot_phase - 35) / 13.0
    head = progress * (height + FALL_HEIGHT) - FALL_HEIGHT
    if wave_y < head - FALL_HEIGHT:
        return 0.0
    if wave_y < head:
        return 0.32
    if wave_y < head + FALL_HEIGHT:
        return 0.62
    return 1.0


def waterfall_art(art: list[str], slot_phase: int, frame_number: int) -> list[str]:
    height = len(art)
    flowed: list[str] = []

    for y, line in enumerate(art):
        chars: list[str] = []
        for x, char in enumerate(line):
            if char == EMPTY or char == " ":
                chars.append(char)
                continue

            visibility = waterfall_visibility(slot_phase, x, y, height)
            if visibility >= 1.0:
                chars.append(char)
            elif visibility <= 0.0:
                chars.append(EMPTY)
            else:
                chars.append(char if noise(x, y, frame_number) < visibility * 100 else EMPTY)
        flowed.append("".join(chars))

    return flowed


def has_visible_text(rows: list[str]) -> bool:
    return any(row.strip(EMPTY).strip() for row in rows)


def position_limits(art: list[str], *, sign: bool) -> tuple[int, int]:
    columns, lines = terminal_size()
    art_width = max(len(line) for line in art)
    art_height = len(art)
    sign_width = max(len(line) for line in SIGN_LINES) + 3 if sign else 0
    max_x = max(0, columns - art_width - sign_width - 1)
    max_y = max(0, lines - art_height - 1)
    return max_x, max_y


def pick_positions(rng: random.Random, art: list[str], *, sign: bool) -> list[tuple[int, int]]:
    max_x, max_y = position_limits(art, sign=sign)
    positions: list[tuple[int, int]] = []

    for _ in range(SLOT_COUNT):
        position = (rng.randint(0, max_x), rng.randint(0, max_y))
        for _ in range(8):
            if not positions:
                break
            last_x, last_y = positions[-1]
            distance = abs(position[0] - last_x) + abs(position[1] - last_y)
            if distance >= 8 or (max_x == 0 and max_y == 0):
                break
            position = (rng.randint(0, max_x), rng.randint(0, max_y))
        positions.append(position)

    return positions


def append_skyy_sign(row: str, sign_index: int) -> str:
    if sign_index >= len(SIGN_LINES):
        return row
    return f"{row.rstrip(EMPTY)}   {SIGN_LINES[sign_index]}"


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
    positions: list[tuple[int, int]],
    *,
    sign: bool = True,
    crop: bool = False,
) -> str:
    cycle_index = (frame_number - 1) % FRAME_COUNT
    slot_index = cycle_index // SLOT_LENGTH
    slot_phase = cycle_index % SLOT_LENGTH
    x, y = positions[slot_index]
    show_sign = sign and slot_phase == 17

    sk = blink_art(art, slot_phase)
    sk = waterfall_art(sk, slot_phase, frame_number)
    if not show_sign and not has_visible_text(sk):
        return ""

    rows: list[str] = ["" for _ in range(y)]
    for row_index, line in enumerate(sk):
        row = " " * x + line.rstrip(EMPTY)
        if show_sign and row_index < len(SIGN_LINES):
            row = append_skyy_sign(row, row_index)
        rows.append(row)

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(
    art: list[str],
    rng: random.Random,
    *,
    sign: bool,
    crop: bool,
) -> list[str]:
    positions = pick_positions(rng, art, sign=sign)
    return [
        render_frame(art, frame_number, positions, sign=sign, crop=crop)
        for frame_number in range(1, FRAME_COUNT + 1)
    ]


def validate(art: list[str], frames: list[str], *, sign: bool) -> None:
    if not art:
        raise ValueError("The source art has no lines.")
    if max(len(line) for line in art) == 0:
        raise ValueError("The source art has no visible width.")
    if len(frames) != FRAME_COUNT:
        raise ValueError(f"Expected {FRAME_COUNT} frames, got {len(frames)}.")
    if all(frame == frames[0] for frame in frames[1:]):
        raise ValueError("Generated frames are identical.")
    if not any(frame == "" for frame in frames):
        raise ValueError("The art never fully disappears.")
    if not any(frame.strip(EMPTY).strip() for frame in frames):
        raise ValueError("The art never appears.")
    if sign and "Skyy" not in "\n".join(frames):
        raise ValueError("The Skyy sign is missing.")


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def animate(
    art: list[str],
    rng: random.Random,
    *,
    delay: float,
    sign: bool,
    crop: bool,
) -> None:
    sys.stdout.write("\033[?25l")
    try:
        while True:
            positions = pick_positions(rng, art, sign=sign)
            for frame_number in range(1, FRAME_COUNT + 1):
                clear_screen()
                frame = render_frame(art, frame_number, positions, sign=sign, crop=crop)
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
    parser = argparse.ArgumentParser(description="Animate the Sk art as a random waterfall.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print one 200-frame cycle")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--seed", type=int, help="use repeatable random positions")
    parser.add_argument("--no-sign", action="store_true", help="hide the Skyy sign")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    sign = not args.no_sign
    rng = random.Random(args.seed)
    art = load_art(args.source)
    frames = build_frames(art, rng, sign=sign, crop=args.crop)
    validate(art, frames, sign=sign)

    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0

    animate(art, rng, delay=delay, sign=sign, crop=args.crop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
