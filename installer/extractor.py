"""
extractor.py - Archive extraction utility.

Supports .zip, .tar.gz, .tgz, and .tar.xz archives.
All archives are extracted into the supplied destination directory.
"""

import os
import tarfile
import zipfile


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
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest_dir)
    elif archive_path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(dest_dir)
    elif archive_path.endswith(".tar.xz"):
        with tarfile.open(archive_path, "r:xz") as tf:
            tf.extractall(dest_dir)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")
