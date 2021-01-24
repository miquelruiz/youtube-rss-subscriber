from typing import Any, Dict, List, Optional, cast
from pathlib import Path

import yaml


CONFIG_FILE_NAME = "config.yml"
CONFIG_DIRS = (
    Path.home() / Path(".yrs"),
    Path("/etc/youtube-rss-subscriber"),
)


class Config:
    _instance: Optional["Config"] = None
    _config: Dict[str, Any]
    _required_keys: List[str] = ["database_url"]

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)

            config_file_path = None
            for c in CONFIG_DIRS:
                file_path = c / Path(CONFIG_FILE_NAME)
                if c.is_dir() and file_path.is_file():
                    config_file_path = file_path

            if config_file_path is None:
                config_file_path = init()

            with open(config_file_path, "r") as cfile:
                cls._config = cast(Dict[str, Any], yaml.safe_load(cfile))

            for k in cls._required_keys:
                try:
                    cls._config[k]
                except KeyError:
                    raise RuntimeError(f"Invalid configuration: '{k}' missing")

        return cls._instance

    @property
    def database_url(self) -> str:
        return cast(str, self._config["database_url"])

    @property
    def youtube_dl_opts(self) -> Dict[str, Any]:
        return cast(Dict[str, Any], self._config["youtube_dl_opts"])


def init() -> Path:
    config_dir = CONFIG_DIRS[0]
    config_dir.mkdir(exist_ok=True)
    config_file_path = config_dir / Path(CONFIG_FILE_NAME)
    with open(config_file_path, "w") as cfile:
        yaml.dump(
            {
                "database_url": f"sqlite:///{config_dir}/yrs.db",
                "youtube_dl_opts": {
                    "outtmpl": "%(title)s-%(id)s.%(ext)s",
                },
            },
            stream=cfile,
        )
    print(f"Config file created in {config_file_path}")
    return config_file_path
