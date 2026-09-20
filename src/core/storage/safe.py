from __future__ import annotations

from pathlib import Path


def validate_storage_key(key: str) -> None:
    """Reject keys that could escape a storage root (traversal, absolute, separators)."""
    if not key or "\x00" in key or "\\" in key:
        raise ValueError(f"Invalid storage key: {key!r}")
    if Path(key).is_absolute() or ".." in Path(key).parts:
        raise ValueError(f"Invalid storage key: {key!r}")


def safe_storage_parts(workspace_id: str, ko_id: str, filename: str) -> tuple[str, str, str]:
    """Validate structural components; reduce filename to its basename."""
    for label, part in (("workspace_id", workspace_id), ("ko_id", ko_id)):
        if not part or part in (".", "..") or "\\" in part or "\x00" in part:
            raise ValueError(f"Invalid {label}: {part!r}")
        if Path(part).name != part:
            raise ValueError(f"Invalid {label}: {part!r}")
    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", "..") or "\\" in safe_name or "\x00" in safe_name:
        raise ValueError(f"Invalid filename: {filename!r}")
    return workspace_id, ko_id, safe_name


def safe_resolved(base: Path, key: str) -> Path:
    """Resolve a key under base, rejecting any path that escapes it."""
    validate_storage_key(key)
    resolved = (base / key).resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError(f"Storage key escapes base: {key!r}")
    return resolved
