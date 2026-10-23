"""Checks for native runtime libraries needed by the desktop application."""

from ctypes.util import find_library
from collections.abc import Callable


def missing_linux_runtime_dependencies(
    library_finder: Callable[[str], str | None] = find_library,
) -> tuple[str, ...]:
    """Return user-facing names of missing GTK/WebKit libraries on Linux."""
    required = {
        "GTK 3": ("gtk-3",),
        "WebKitGTK": ("webkit2gtk-4.1", "webkit2gtk-4.0"),
    }
    return tuple(
        label
        for label, candidates in required.items()
        if not any(library_finder(candidate) for candidate in candidates)
    )
