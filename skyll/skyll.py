#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import sys
import time
from pathlib import Path


ART_PATH = Path(__file__).with_name("text.md")
EMPTY = "\u2800"
FRAME_COUNT = 72
FRAME_DELAY = 1.0 / 20.0
POSE_HOLD = 6
CAPTIONS = ("SKYLL", "SKY DRIFT", "SKYLL", "SKY DRIFT")
FRAME_LABEL = re.compile(r"^\s*frame\s+\d+\b", re.IGNORECASE)


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def trim_empty_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def split_source_frames(text: str) -> list[list[str]]:
    frames: list[list[str]] = []
    current: list[str] = []
    blank_run = 0

    for line in text.splitlines():
        if FRAME_LABEL.match(line):
            if trim_empty_edges(current):
                frames.append(current)
            current = []
            blank_run = 0
            continue

        if line.strip():
            blank_run = 0
            current.append(line.rstrip())
            continue

        blank_run += 1
        if blank_run >= 2:
            if trim_empty_edges(current):
                frames.append(current)
            current = []
        elif current:
            current.append("")

    if trim_empty_edges(current):
        frames.append(current)

    return frames


def normalize_frame(lines: list[str]) -> list[str]:
    width = max(len(line) for line in lines)
    return [line.ljust(width, EMPTY) for line in lines]


def load_frames(path: Path) -> list[list[str]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the skyll art in text.md.") from error

    frames = [normalize_frame(frame) for frame in split_source_frames(text)]
    if not frames:
        raise SystemExit(f"{path} is empty.")
    return frames


def move_line(line: str, offset: int) -> str:
    if offset > 0:
        return EMPTY * offset + line
    if offset < 0:
        return line[-offset:] + EMPTY * min(-offset, 16)
    return line


def crop_to_terminal(rows: list[str]) -> list[str]:
    columns, lines = shutil.get_terminal_size(fallback=(100, 38))
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def caption_for(frame_number: int) -> str:
    return CAPTIONS[((frame_number - 1) // 18) % len(CAPTIONS)]


def pick_pose(frames: list[list[str]], frame_number: int) -> list[str]:
    pose_index = ((frame_number - 1) // POSE_HOLD) % len(frames)
    return frames[pose_index]


def render_frame(
    source_frames: list[list[str]],
    frame_number: int,
    *,
    caption: bool = True,
    crop: bool = False,
) -> str:
    pose = pick_pose(source_frames, frame_number)
    phase = 2.0 * math.pi * ((frame_number - 1) % FRAME_COUNT) / FRAME_COUNT
    wind = round(math.sin(phase) * 8.0)
    float_y = round((math.sin(phase * 1.5) + 1.0) * 1.5)
    tilt = round(math.sin(phase * 2.0 + 0.45) * 2.0)
    tail_sway = round(math.sin(phase * 3.5 - 0.3) * 3.0)
    sparkle = math.sin(phase * 4.0)
    base_indent = 8

    rows: list[str] = ["" for _ in range(float_y)]
    center_y = max(1, len(pose) // 2)

    for y, line in enumerate(pose):
        row_wave = round(math.sin(phase * 2.3 + y * 0.42) * 1.5)
        section_sway = tilt if y < center_y else -tilt + tail_sway
        offset = base_indent + wind + row_wave + section_sway
        rows.append(move_line(line, offset))

    cloud_indent = max(0, base_indent + wind - 4)
    cloud = f"{' ' * cloud_indent}.  .    .   ."
    if sparkle > 0.55:
        rows.insert(0, cloud)
    elif sparkle < -0.55:
        rows.append(cloud[::-1])

    if caption:
        marker = ">" if sparkle >= 0 else "<"
        label = caption_for(frame_number)
        indent = max(0, base_indent + wind + 11)
        rows.extend(("", f"{' ' * indent}{marker} {label} {marker}"))

    if crop:
        rows = crop_to_terminal(rows)
    return "\n".join(rows)


def build_frames(
    source_frames: list[list[str]],
    count: int,
    *,
    caption: bool,
    crop: bool,
) -> list[str]:
    return [
        render_frame(source_frames, frame_number, caption=caption, crop=crop)
        for frame_number in range(1, count + 1)
    ]


def validate(source_frames: list[list[str]], frames: list[str]) -> None:
    if not source_frames:
        raise ValueError("The source art has no frames.")
    if not any(line.strip() for frame in source_frames for line in frame):
        raise ValueError("The source art has no visible characters.")
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
    parser = argparse.ArgumentParser(description="Animate the skyll AA art from text.md.")
    parser.add_argument("delay", nargs="?", type=float, default=FRAME_DELAY)
    parser.add_argument("--source", type=Path, default=ART_PATH, help="art file to animate")
    parser.add_argument("--frames", type=int, default=FRAME_COUNT, help="number of animation frames")
    parser.add_argument("--once", action="store_true", help="print the generated frames once")
    parser.add_argument("--check", action="store_true", help="validate without animating")
    parser.add_argument("--caption", action="store_true", help="show the title caption")
    parser.add_argument("--no-caption", action="store_true", help="keep the title caption hidden")
    parser.add_argument("--crop", action="store_true", help="crop frames to the terminal size")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_terminal()
    args = parse_args(sys.argv[1:] if argv is None else argv)

    delay = max(0.01, args.delay)
    frame_count = max(2, args.frames)
    source_frames = load_frames(args.source)
    frames = build_frames(
        source_frames,
        frame_count,
        caption=args.caption and not args.no_caption,
        crop=args.crop,
    )
    validate(source_frames, frames)

    if args.check:
        return 0
    if args.once:
        print_frames(frames)
        return 0

    animate(frames, delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
