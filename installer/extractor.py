"""
extractor.py - Archive extraction utility.

Supports .zip, .tar.gz, .tgz, and .tar.xz archives.
All archives are extracted into the supplied destination directory.
"""

import os
import stat
import tarfile
import zipfile
from pathlib import Path


def _safe_member_path(dest_dir: str, member_name: str) -> Path:
    """Resolve an archive member and reject traversal or absolute paths."""
    destination = Path(dest_dir).resolve()
    member_path = Path(member_name)
    if member_path.is_absolute() or member_path.anchor:
        raise ValueError(f"Unsafe absolute archive path: {member_name}")

    resolved = (destination / member_path).resolve()
    try:
        resolved.relative_to(destination)
    except ValueError as exc:
        raise ValueError(f"Unsafe archive path: {member_name}") from exc
    return resolved


def _restore_mode(path: Path, mode: int) -> None:
    """Restore executable/read-only bits when the archive contains them."""
    permissions = stat.S_IMODE(mode)
    if permissions:
        os.chmod(path, permissions)


def _extract_zip(archive_path: str, dest_dir: str) -> None:
    with zipfile.ZipFile(archive_path, "r") as zf:
        for info in zf.infolist():
            target = _safe_member_path(dest_dir, info.filename)
            is_directory = info.is_dir() or info.filename.endswith("/")
            if is_directory:
                target.mkdir(parents=True, exist_ok=True)
                _restore_mode(target, info.external_attr >> 16)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, "r") as source, target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
            _restore_mode(target, info.external_attr >> 16)


def _extract_tar(archive_path: str, dest_dir: str, mode: str) -> None:
    with tarfile.open(archive_path, mode) as tf:
        for member in tf.getmembers():
            target = _safe_member_path(dest_dir, member.name)
            if member.issym() or member.islnk():
                raise ValueError(f"Symbolic and hard links are not allowed: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                _restore_mode(target, member.mode)
                continue
            if not member.isfile():
                raise ValueError(f"Unsupported archive member: {member.name}")

            target.parent.mkdir(parents=True, exist_ok=True)
            source = tf.extractfile(member)
            if source is None:
                raise ValueError(f"Unable to read archive member: {member.name}")
            with source, target.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
            _restore_mode(target, member.mode)


def extract_archive(archive_path: str, dest_dir: str) -> None:
    """Extract *archive_path* into *dest_dir*, creating it if necessary.

    Supported formats: .zip, .tar.gz, .tgz, .tar.xz

    Args:
        archive_path: Absolute or relative path to the archive file.
        dest_dir: Directory into which files are extracted.

    Raises:
        ValueError: If the archive format is not supported.
        FileNotFoundError: If *archive_path* does not exist.
    """
    os.makedirs(dest_dir, exist_ok=True)

    if archive_path.endswith(".zip"):
        _extract_zip(archive_path, dest_dir)
    elif archive_path.endswith((".tar.gz", ".tgz")):
        _extract_tar(archive_path, dest_dir, "r:gz")
    elif archive_path.endswith(".tar.xz"):
        _extract_tar(archive_path, dest_dir, "r:xz")
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")
