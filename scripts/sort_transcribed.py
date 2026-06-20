"""
Sorts files in a directory into "TO DO" (not yet transcribed) and "DONE" (already transcribed).

A file is considered "DONE" if there is a .txt transcription with the same base name
in the same folder. A file is considered "TO DO" if no matching .txt exists.

By default only video/audio files are considered as source files. The script moves
(or optionally copies) them — together with their companion files (e.g. extracted
audio or transcription) — into the appropriate subfolder.

Usage:
    python sort_transcribed.py /path/to/directory

Options:
    --copy      Copy files instead of moving them (default: move)
    --dry-run   Only print what would happen, without actually moving/copying anything
"""

import argparse
import shutil
from pathlib import Path

# Extensions treated as "source" media files (video or audio originals).
# Companion files (.txt, other audio formats, etc.) are inferred from these.
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".opus"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def sort_files(directory: str, copy: bool = False, dry_run: bool = False):
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"Error: Directory '{directory}' does not exist.")
        return

    da_fare_dir = dir_path / "TO DO"
    DONE_dir   = dir_path / "DONE"

    # Collect all files (non-recursive)
    all_files = [f for f in dir_path.iterdir() if f.is_file()]

    # Index transcript stems: a transcript is named "<stem>_transcript.txt"
    # so we extract the original stem by stripping the "_transcript" suffix.
    txt_stems = set()
    for f in all_files:
        if f.suffix.lower() == ".txt" and f.stem.endswith("_transcript"):
            original_stem = f.stem[: -len("_transcript")]
            txt_stems.add(original_stem)

    # Group media files by stem — each stem is processed exactly once.
    # This avoids double-moves when both .mp3 and .mp4 share the same name.
    media_stems: dict[str, list[Path]] = {}
    for f in all_files:
        if f.suffix.lower() in MEDIA_EXTENSIONS:
            media_stems.setdefault(f.stem, []).append(f)

    if not media_stems:
        print("No media files found in the directory.")
        return

    # Build a file index by name for safe "already moved" checks
    all_files_by_name: dict[str, Path] = {f.name: f for f in all_files}

    todo_stems = []
    done_stems = []

    for stem in sorted(media_stems):
        if stem in txt_stems:
            done_stems.append(stem)
        else:
            todo_stems.append(stem)

    action = "Copy" if copy else "Move"

    def transfer(file: Path, destination_dir: Path):
        if not file.exists():
            return  # already moved (shouldn't happen, but safe guard)
        dest = destination_dir / file.name
        if dry_run:
            print(f"    [DRY RUN] {action}: {file.name}  →  {destination_dir.name}/")
            return
        destination_dir.mkdir(parents=True, exist_ok=True)
        if copy:
            shutil.copy2(file, dest)
        else:
            shutil.move(str(file), dest)

    def transfer_group(stem: str, destination_dir: Path):
        """Transfer all files belonging to a stem (video, audio, transcript)."""
        transcript_name = f"{stem}_transcript.txt"
        group = [
            f for f in all_files
            if f.stem == stem or f.name == transcript_name
        ]
        for f in sorted(group, key=lambda x: x.name):
            transfer(f, destination_dir)

    print(f"\n{'=' * 50}")
    print(f"  Directory : {dir_path}")
    print(f"  Action    : {'Copy (dry run)' if dry_run and copy else 'Move (dry run)' if dry_run else action}")
    print(f"{'=' * 50}\n")

    print(f"📋 TO DO ({len(todo_stems)} group{'s' if len(todo_stems) != 1 else ''}):")
    if todo_stems:
        for stem in todo_stems:
            files = sorted(media_stems[stem], key=lambda f: f.name)
            print(f"  - {stem}  ({', '.join(f.suffix for f in files)})")
            transfer_group(stem, da_fare_dir)
    else:
        print("  (nessuno)")

    print(f"\n✅ DONE ({len(done_stems)} group{'s' if len(done_stems) != 1 else ''}):")
    if done_stems:
        for stem in done_stems:
            files = sorted(media_stems[stem], key=lambda f: f.name)
            print(f"  - {stem}  ({', '.join(f.suffix for f in files)})")
            transfer_group(stem, DONE_dir)
    else:
        print("  (nessuno)")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sort media files into 'TO DO' and 'DONE' based on transcription presence."
    )
    parser.add_argument("directory", help="The directory to process")
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without actually moving/copying files",
    )
    args = parser.parse_args()

    sort_files(args.directory, copy=args.copy, dry_run=args.dry_run)
