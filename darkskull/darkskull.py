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
FILL = "\u28ff"
FRAME_COUNT = 78
FRAME_DELAY = 1.0 / 23.0
CAPTIONS = ("DARK SKULL", "SHADOW PULSE", "NIGHT SHIFT", "DARK SKULL")


def configure_terminal() -> None:
    if os.name == "nt":
        os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_art(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise SystemExit(f"Could not find {path}. Put the dark skull art in text.md.") from error

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
    columns, lines = shutil.get_terminal_size(fallback=(120, 46))
    if columns > 10:
        rows = [row[: columns - 1] for row in rows]
    if lines > 6 and len(rows) > lines - 1:
        rows = rows[: lines - 1]
    return rows


def caption_for(frame_number: int) -> str:
    return CAPTIONS[((frame_number - 1) // 19) % len(CAPTIONS)]


def render_frame(
    art: list[str],
    frame_number: int,
    *,
    caption: bool = True,
    crop: bool = False,
) -> str:
    phase = 2.0 * math.pi * ((frame_number - 1) % FRAME_COUNT) / FRAME_COUNT
    pulse = math.sin(phase * 3.0)
    float_y = round((math.sin(phase * 1.2) + 1.0) * 1.5)
    drift = round(math.sin(phase) * 6.0)
    face_pull = round(math.sin(phase * 2.4 + 0.6) * 3.0)
    jaw_drag = round(math.sin(phase * 4.8 - 0.5) * 4.0)
    tremor = round(math.sin(phase * 19.0) * 2.0) if abs(pulse) > 0.55 else 0
    base_indent = 1

    rows = [FILL * (len(art[0]) + base_indent + 24) for _ in range(float_y)]
    height = len(art)

    for y, line in enumerate(art):
        row_wave = round(math.sin(phase * 2.7 + y * 0.31) * 2.0)
        glitch = round(math.sin(phase * 11.0 + y * 1.7) * 2.0) if y % 7 == frame_number % 7 else 0
        offset = base_indent + drift + tremor + row_wave + glitch

        if y < height * 0.28:
            offset += round(face_pull * 0.6)
        elif y < height * 0.68:
            offset += face_pull
        else:
            offset += jaw_drag

        rows.append(move_line(line, offset))

    if pulse > 0.7:
        slash_indent = max(0, base_indent + drift + 3)
        rows.insert(float_y + 2, FILL * slash_indent + "//// SHADOW RIPPLE ////")
    elif pulse < -0.7:
        slash_indent = max(0, base_indent + drift + 5)
        rows.append(FILL * slash_indent + "\\\\\\\\ SHADOW RIPPLE \\\\\\\\")

    if caption:
        marker = ">" if pulse >= 0 else "<"
        label = caption_for(frame_number)
        indent = max(0, base_indent + drift + 24)
        rows.extend(("", f"{' ' * indent}{marker} {label} {marker}"))

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
    parser = argparse.ArgumentParser(description="Animate the dark skull art from text.md.")
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
