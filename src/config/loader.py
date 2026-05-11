
from pathlib import Path
from src.config.config import Config
from platformdirs import user_config_dir

def get_config_dir() -> Path:
    return Path(user_config_dir("cc-mimic"))

def load_config(cwd: Path | None) -> Config:
    cwd = cwd or Path.cwd()

