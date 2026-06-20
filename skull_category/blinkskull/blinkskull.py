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
FRAME_COUNT = 124
SLOT_COUNT = 4
SLOT_LENGTH = FRAME_COUNT // SLOT_COUNT
FRAME_DELAY = 1.0 / 20.0
SIGN_LINES = (
    "+-------+",
    "|  Sky  |",
    "+---+---+",
    "    |",
)
EYE_ROWS = (4, 5, 6)
EYE_SPANS = ((5, 4), (12, 4))


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the blinkskull art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(96, 32))


def replace_span(chars: list[str], start: int, replacement: str) -> None:
    for index, char in enumerate(replacement):
        position = start + index
        if 0 <= position < len(chars):
            chars[position] = char


def blink_state(slot_phase: int) -> str:
    if slot_phase in (10, 14, 21, 25):
        return "half"
    if slot_phase in (11, 12, 13, 22, 23, 24):
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


def visibility_for(slot_phase: int) -> float:
    if slot_phase <= 2 or slot_phase >= 30:
        return 0.0
    if slot_phase == 3:
        return 0.25
    if slot_phase == 4:
        return 0.55
    if slot_phase == 5:
        return 0.85
    if slot_phase <= 25:
        return 1.0
    return {26: 0.7, 27: 0.45, 28: 0.22, 29: 0.08}[slot_phase]


def fade_art(art: list[str], visibility: float, salt: int) -> list[str]:
    if visibility >= 1.0:
        return art

    faded: list[str] = []
    threshold = round(visibility * 100)
    for y, line in enumerate(art):
        chars: list[str] = []
        for x, char in enumerate(line):
            if char == EMPTY or char == " ":
                chars.append(char)
                continue
            sparkle = (x * 37 + y * 53 + salt * 19) % 100
            chars.append(char if sparkle < threshold else EMPTY)
        faded.append("".join(chars))
    return faded


def frame_position_limits(art: list[str], sign: bool) -> tuple[int, int]:
    columns, lines = terminal_size()
    art_width = max(len(line) for line in art)
    art_height = len(art)
    sign_width = max(len(line) for line in SIGN_LINES) + 3 if sign else 0
    draw_width = art_width + sign_width
    draw_height = max(art_height, len(SIGN_LINES))
    max_x = max(0, columns - draw_width - 1)
    max_y = max(0, lines - draw_height - 1)
    return max_x, max_y


def pick_positions(
    rng: random.Random,
    art: list[str],
    *,
    sign: bool,
) -> list[tuple[int, int]]:
    max_x, max_y = frame_position_limits(art, sign)
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


def append_sky_sign(row: str, sign_index: int) -> str:
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
    visibility = visibility_for(slot_phase)
    if visibility <= 0.0:
        return ""

    x, y = positions[slot_index]
    phase = 2.0 * math.pi * slot_phase / SLOT_LENGTH
    drift_x = round(math.sin(phase) * 1.0)
    drift_y = 1 if math.sin(phase * 2.0) > 0.65 else 0
    show_sign = sign and slot_phase == 5

    skull = blink_art(art, slot_phase)
    skull = fade_art(skull, visibility, frame_number + slot_index * 17)

    rows: list[str] = ["" for _ in range(y + drift_y)]
    for row_index, line in enumerate(skull):
        row = " " * max(0, x + drift_x) + line.rstrip(EMPTY)
        if show_sign and row_index < len(SIGN_LINES):
            row = append_sky_sign(row, row_index)
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
        raise ValueError("The skull never fully disappears.")
    if sign and "Sky" not in "\n".join(frames):
        raise ValueError("The Sky sign is missing.")


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
    parser = argparse.ArgumentParser(description="Animate the blinkskull art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--once", action="store_true", help="print one 124-frame cycle")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--seed", type=int, help="use repeatable random positions")
    parser.add_argument("--no-sign", action="store_true", help="hide the Sky sign")
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
