from pathlib import Path


def resolve_path(
    base: str | Path,
    path: str, # path that tool thrown at us like cwd
):
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    return Path(base).resolve() / path #user/nbest/Desktop/cc-mimic + tools/base.py -> base + path


def is_binary_file(
    path: str| Path
) -> bool:
    try:
        with open(path, "rb") as f:
            chuck = f.read(8192)
            return f"\x00" in chuck # logic to checking binary file
    except (OSError, IOError):
        return False