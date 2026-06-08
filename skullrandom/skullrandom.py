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
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMPTY = "\u2800"
FRAME_COUNT = 200
SLOT_COUNT = 5
SLOT_LENGTH = FRAME_COUNT // SLOT_COUNT
FRAME_DELAY = 1.0 / 20.0
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


def has_visible_text(lines: list[str]) -> bool:
    return any(line.strip(EMPTY).strip() for line in lines)


def trim_invisible_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip(EMPTY).strip():
        lines.pop(0)
    while lines and not lines[-1].strip(EMPTY).strip():
        lines.pop()
    return lines


def normalize_block(lines: list[str]) -> list[str]:
    block = trim_invisible_edges([line.rstrip() for line in lines])
    if not block:
        return []

    width = max(len(line) for line in block)
    return [line.ljust(width, EMPTY) for line in block]


def split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    blank_run = 0

    for line in text.splitlines():
        if line.strip():
            blank_run = 0
            current.append(line)
            continue

        blank_run += 1
        if blank_run >= 2:
            block = normalize_block(current)
            if block:
                blocks.append(block)
            current = []
        elif current:
            current.append("")

    block = normalize_block(current)
    if block:
        blocks.append(block)

    return blocks


def text_paths(*, all_texts: bool) -> list[Path]:
    if not all_texts:
        return [ART_PATH]

    paths = sorted(PROJECT_ROOT.rglob("text.md"))
    return [path for path in paths if ".git" not in path.parts]


def load_blocks(paths: list[Path]) -> list[list[str]]:
    blocks: list[list[str]] = []

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            continue

        for block in split_blocks(text):
            if has_visible_text(block):
                blocks.append(block)

    if not blocks:
        raise SystemExit("No ASCII art blocks found in text.md files.")

    return blocks


def terminal_size() -> tuple[int, int]:
    return shutil.get_terminal_size(fallback=(118, 42))


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = terminal_size()
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def position_limits(art: list[str]) -> tuple[int, int]:
    columns, lines = terminal_size()
    width = max(len(line) for line in art)
    height = len(art)
    return max(0, columns - width - 1), max(0, lines - height - 1)


def pick_events(rng: random.Random, blocks: list[list[str]]) -> list[tuple[int, int, int]]:
    events: list[tuple[int, int, int]] = []

    for _ in range(SLOT_COUNT):
        block_index = rng.randrange(len(blocks))
        max_x, max_y = position_limits(blocks[block_index])
        position = (rng.randint(0, max_x), rng.randint(0, max_y))

        for _ in range(8):
            if not events:
                break
            _, last_x, last_y = events[-1]
            distance = abs(position[0] - last_x) + abs(position[1] - last_y)
            if distance >= 8 or (max_x == 0 and max_y == 0):
                break
            position = (rng.randint(0, max_x), rng.randint(0, max_y))

        events.append((block_index, position[0], position[1]))

    return events


def visibility_for(slot_phase: int) -> float:
    if slot_phase <= 3 or slot_phase >= 38:
        return 0.0
    if slot_phase <= 7:
        return (slot_phase - 3) / 4.0
    if slot_phase <= 29:
        return 1.0
    return max(0.0, (38 - slot_phase) / 8.0)


def fade_art(art: list[str], visibility: float, frame_number: int) -> list[str]:
    if visibility >= 1.0:
        return art

    threshold = round(visibility * 100)
    faded: list[str] = []

    for y, line in enumerate(art):
        chars: list[str] = []
        for x, char in enumerate(line):
            if char == EMPTY or char == " ":
                chars.append(char)
                continue
            sparkle = (x * 37 + y * 53 + frame_number * 19) % 100
            chars.append(char if sparkle < threshold else EMPTY)
        faded.append("".join(chars))

    return faded


def replace_span(chars: list[str], start: int, replacement: str) -> None:
    for index, char in enumerate(replacement):
        position = start + index
        if 0 <= position < len(chars):
            chars[position] = char


def blink_state(slot_phase: int) -> str:
    if slot_phase in (13, 17, 24, 28):
        return "half"
    if slot_phase in (14, 15, 16, 25, 26, 27):
        return "closed"
    return "open"


def blink_art(art: list[str], slot_phase: int) -> list[str]:
    state = blink_state(slot_phase)
    if state == "open":
        return art

    height = len(art)
    width = max(len(line) for line in art)
    if height < 4 or width < 8:
        return art

    lines = [list(line) for line in art]
    lid_row = max(1, min(height - 2, round(height * 0.32)))
    upper_row = lid_row - 1
    lower_row = lid_row + 1
    eye_width = max(3, min(8, width // 10))
    left_start = max(0, round(width * 0.32) - eye_width // 2)
    right_start = max(0, round(width * 0.62) - eye_width // 2)
    lid_char = "_" if state == "half" else "-"

    for start in (left_start, right_start):
        replace_span(lines[upper_row], start, EMPTY * eye_width)
        replace_span(lines[lid_row], start, lid_char * eye_width)
        replace_span(lines[lower_row], start, EMPTY * eye_width)

    return ["".join(line) for line in lines]


def overlay_lines(rows: list[str], overlay: tuple[str, ...], x: int, y: int) -> list[str]:
    rows = rows[:]
    while len(rows) < y + len(overlay):
        rows.append("")

    for offset, text in enumerate(overlay):
        row_index = y + offset
        row = rows[row_index]
        if len(row) < x:
            row += " " * (x - len(row))
        rows[row_index] = row[:x] + text + row[x + len(text) :]

    return rows


def render_frame(
    blocks: list[list[str]],
    events: list[tuple[int, int, int]],
    frame_number: int,
    *,
    crop: bool = True,
) -> str:
    cycle_index = (frame_number - 1) % FRAME_COUNT
    slot_index = cycle_index // SLOT_LENGTH
    slot_phase = cycle_index % SLOT_LENGTH
    block_index, x, y = events[slot_index]
    visibility = visibility_for(slot_phase)
    rows: list[str] = []

    if visibility > 0.0:
        phase = 2.0 * math.pi * slot_phase / SLOT_LENGTH
        drift_x = round(math.sin(phase) * 1.0)
        drift_y = 1 if math.sin(phase * 2.0) > 0.65 else 0
        art = blink_art(blocks[block_index], slot_phase)
        art = fade_art(art, visibility, frame_number)

        rows = ["" for _ in range(y + drift_y)]
        for line in art:
            rows.append(" " * max(0, x + drift_x) + line.rstrip(EMPTY))

    rows = overlay_lines(rows, SIGN_LINES, 2, 1)

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(
    blocks: list[list[str]],
    rng: random.Random,
    *,
    crop: bool,
) -> list[str]:
    events = pick_events(rng, blocks)
    return [
        render_frame(blocks, events, frame_number, crop=crop)
        for frame_number in range(1, FRAME_COUNT + 1)
    ]


def validate(blocks: list[list[str]], frames: list[str]) -> None:
    if not blocks:
        raise ValueError("No art blocks loaded.")
    if len(frames) != FRAME_COUNT:
        raise ValueError(f"Expected {FRAME_COUNT} frames, got {len(frames)}.")
    if all(frame == frames[0] for frame in frames[1:]):
        raise ValueError("Generated frames are identical.")
    if not all("Skyy" in frame for frame in frames):
        raise ValueError("The static Skyy sign is missing from at least one frame.")


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def animate(
    blocks: list[list[str]],
    rng: random.Random,
    *,
    delay: float,
    crop: bool,
) -> None:
    sys.stdout.write("\033[?25l")
    try:
        while True:
            events = pick_events(rng, blocks)
            for frame_number in range(1, FRAME_COUNT + 1):
                clear_screen()
                frame = render_frame(blocks, events, frame_number, crop=crop)
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
    parser = argparse.ArgumentParser(description="Randomly spawn blinking ASCII art from skullrandom/text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to use")
    parser.add_argument("--all-texts", action="store_true", help="use every text.md in the project")
    parser.add_argument("--once", action="store_true", help="print one 200-frame cycle")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--seed", type=int, help="use repeatable random art and positions")
    parser.add_argument("--no-crop", action="store_true", help="do not crop frames to terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    rng = random.Random(args.seed)
    paths = text_paths(all_texts=args.all_texts)
    if not args.all_texts:
        paths = [args.source]
    blocks = load_blocks(paths)
    frames = build_frames(blocks, rng, crop=not args.no_crop)
    validate(blocks, frames)

    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0

    animate(blocks, rng, delay=delay, crop=not args.no_crop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
