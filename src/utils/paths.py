from pathlib import Path
import yaml

def resolve_path(
    base: str | Path,
    path: str,  # path that tool thrown at us like cwd
):
    path = Path(path)
    if path.is_absolute():
        return path.resolve()
    return (
        Path(base).resolve() / path
    )  # user/nbest/Desktop/cc-mimic + tools/base.py -> base + path


def display_path_rel_to_cwd(path: str, cwd: Path | None) -> str:
    try:
        p = Path(path)
    except Exception:
        return path

    if cwd:
        try:
            return str(p.relative_to(cwd))
        except ValueError:
            pass

    return str(p)


def ensure_parent_directory(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def is_binary_file(path: str | Path) -> bool:
    try:
        with open(path, "rb") as f:
            chuck = f.read(8192)
            return b"\x00" in chuck  # logic to checking binary file
    except (OSError, IOError):
        return False

def load_frontmatter(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    
    if not raw.startswith("---"):
        return {}, raw
    
    parts = raw.split("---", 2)
    metadata = yaml.safe_load(parts[1])
    body = parts[2].strip()
    
    return metadata, body