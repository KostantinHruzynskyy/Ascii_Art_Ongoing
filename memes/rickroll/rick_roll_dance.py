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
FRAME_COUNT = 64
FRAME_DELAY = 1.0 / 18.0
LYRICS = (
    "Never gonna give you up",
    "Never gonna let you down",
    "Never gonna run around",
    "and desert you",
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
        raise SystemExit(f"Could not find {path}. Put the Rick Roll art in text.md.") from error

    lines = text.splitlines()
    if not lines:
        raise SystemExit(f"{path} is empty.")

    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return EMPTY * offset + line
    if offset < 0:
        return line[-offset:] + EMPTY * min(-offset, 8)
    return line


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = shutil.get_terminal_size(fallback=(100, 42))
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def lyric_for(frame_number: int) -> str:
    lyric_index = ((frame_number - 1) // 12) % len(LYRICS)
    return LYRICS[lyric_index]


def render_frame(
    art: list[str],
    frame_number: int,
    *,
    caption: bool = True,
    crop: bool = True,
) -> str:
    phase = 2.0 * math.pi * ((frame_number - 1) % FRAME_COUNT) / FRAME_COUNT
    beat = math.sin(phase * 2.0)
    bounce = round((beat + 1.0) * 1.25)
    whole_body_sway = round(math.sin(phase) * 4.0)
    shoulder_sway = round(math.sin(phase * 2.0 + 0.9) * 2.0)
    step_sway = round(math.sin(phase * 2.0 - 0.7) * 3.0)
    base_indent = 4

    rows = ["" for _ in range(bounce)]
    center_y = max(1, len(art) // 2)

    for y, line in enumerate(art):
        row_wave = round(math.sin(phase + y * 0.32) * 1.25)
        if y < center_y * 0.65:
            body_offset = shoulder_sway
        elif y < center_y * 1.35:
            body_offset = round(shoulder_sway * 0.5)
        else:
            body_offset = step_sway

        offset = base_indent + whole_body_sway + body_offset + row_wave
        rows.append(move_line(line, offset))

    if caption:
        lyric = lyric_for(frame_number)
        pulse = ">" if beat >= 0 else "<"
        lyric_indent = max(0, base_indent + whole_body_sway + 10)
        rows.extend(("", f"{' ' * lyric_indent}{pulse} {lyric} {pulse}"))

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
    parser = argparse.ArgumentParser(description="Animate the Rick Roll art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--frames", type=int, default=FRAME_COUNT, help="number of animation frames")
    parser.add_argument("--once", action="store_true", help="print the generated frames once")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--no-caption", action="store_true", help="hide the lyric caption")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    frame_count = max(2, args.frames)
    art = load_art(args.source)
    frames = build_frames(
        art,
        frame_count,
        caption=not args.no_caption,
        crop=args.crop,
    )
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
