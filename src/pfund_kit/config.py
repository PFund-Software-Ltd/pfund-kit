from __future__ import annotations

import copy
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Self

from pfund_kit.migration import Migration, migrate
from pfund_kit.paths import ProjectPaths
from pfund_kit.style import RichColor, TextStyle, cprint
from pfund_kit.utils.yaml import dump, load

__all__ = ["Configuration"]


def _to_user_path(value: str | Path, name: str) -> Path:
    """Expand "~" and require an absolute path.

    Path("~/x") is NOT the home dir: pathlib treats "~" as a folder name, so it
    would silently create "./~/x" in whatever dir the program runs from. A
    relative path ("data") has the same problem, so it is rejected too.
    """
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError(
            f"{name} must be an absolute path or start with '~', got {str(value)!r}"
        )
    return path


class Configuration(ABC):
    """Project config stored as a versioned YAML file.

    Subclasses own their fields (via ``_initialize_from_data`` / ``to_dict``)
    and their migrations, registered the same way as ``pfund_kit.settings``:
    ``migrations = {"0.1.0": ("0.1.1", upgrade_to_011)}``. A migration receives
    the stored fields without ``__version__`` and returns them in the shape
    ``to_dict()`` produces. Migration runs before any field is read, and the
    original file is kept as ``config.yaml.<random>.bak`` before it is rewritten.
    """

    __version__: ClassVar[str] = "0.1.0"
    migrations: ClassVar[dict[str, tuple[str, Migration]]] = {}
    # set by pfund_kit.logging.load_logging_config()
    _logging_config_cache: dict[str, Any] | None

    LOGGING_CONFIG_FILENAME = "logging.yaml"
    DOCKER_COMPOSE_FILENAME = "compose.yaml"

    # Files to copy on initialization, mapped to whether they are required.
    # Subclasses can override to add/remove files (e.g. packages without compose.yaml).
    DEFAULT_FILES: ClassVar[dict[str, bool]] = {
        LOGGING_CONFIG_FILENAME: True,
        DOCKER_COMPOSE_FILENAME: False,
    }

    def __init__(self, project_name: str, source_file: str | None = None):
        """
        Args:
            project_name: Name of the project.
            source_file: Path to a source file for determining project layout.
                        If None, auto-detects from the caller's __file__.
        """
        self._paths = ProjectPaths(project_name, source_file)

        # fixed paths, since config_path cannot be changed
        self.config_path = self._paths.config_path
        self.config_filename = "config.yaml"

        # load config file, upgrading an older schema before any field is read
        original = self.file_path.read_bytes() if self.file_path.exists() else None
        stored = load(self.file_path) or {}
        if not isinstance(stored, dict):
            stored = {}
        stored_version = stored.get("__version__")
        # config file is corrupted or missing if __version__ is not present
        if stored_version is None:
            print(
                f"Config file {self.file_path} is corrupted or missing, resetting to default"
            )
            self._data: dict[str, Any] = {}
            needs_save = True
        else:
            needs_save = stored_version != self.__version__
            if needs_save:
                cprint(
                    f"Migrating config from version {stored_version} to {self.__version__}",
                    style=TextStyle.BOLD + RichColor.RED,
                )
            self._data = migrate(
                stored,
                target=self.__version__,
                migrations=self.migrations,
                name="Configuration",
            )

        # Allow subclasses to initialize their attributes from _data
        self._initialize_from_data()

        # configurable paths
        default_data_path = self._paths.data_path
        default_log_path = self._paths.log_path
        default_cache_path = self._paths.cache_path
        try:
            self.data_path = self._data.get("data_path", default_data_path)
            self.log_path = self._data.get("log_path", default_log_path)
            self.cache_path = self._data.get("cache_path", default_cache_path)
        except ValueError as e:
            raise ValueError(f"{e}, fix it in {self.file_path}") from e

        if needs_save:
            if original:
                self._backup(original)
            self.save()

        self.ensure_dirs()
        self._initialize_default_files()

    def scoped(self, *parts: str) -> Self:
        """A copy with data/log/cache nested under `parts`.

        For projects that partition their storage by a sub-identity: pfund by
        engine name, alphafund by fund. A copy rather than an in-place
        narrowing, since a config is typically a process-wide singleton --
        mutating it would nest a second scope inside the first (`logs/a/b`) and
        leak the change to every other holder.

        `config_path` is deliberately not scoped; it is fixed, so a project
        needing a scoped config file builds that path itself.
        """
        scoped = copy.deepcopy(self)
        scoped.data_path = self._data_path.joinpath(*parts)
        scoped.log_path = self._log_path.joinpath(*parts)
        scoped.cache_path = self._cache_path.joinpath(*parts)
        return scoped

    @property
    def path(self):
        return self.config_path

    @property
    def file_path(self):
        return self.config_path / self.config_filename

    @property
    def log_path(self):
        return self._log_path

    @log_path.setter
    def log_path(self, value: str | Path):
        self._log_path = _to_user_path(value, "log_path")

    @property
    def data_path(self):
        return self._data_path

    @data_path.setter
    def data_path(self, value: str | Path):
        self._data_path = _to_user_path(value, "data_path")

    @property
    def cache_path(self):
        return self._cache_path

    @cache_path.setter
    def cache_path(self, value: str | Path):
        self._cache_path = _to_user_path(value, "cache_path")

    @property
    def filename(self):
        """Filename of the config file."""
        return self.config_filename

    @property
    def logging_config_file_path(self):
        return self.config_path / self.LOGGING_CONFIG_FILENAME

    @property
    def docker_compose_file_path(self):
        return self.config_path / self.DOCKER_COMPOSE_FILENAME

    @abstractmethod
    def prepare_docker_context(self):
        """Prepare the context before running docker compose.

        Override this method in project-specific config to perform any setup
        needed before running docker compose (e.g., setting environment variables,
        ensuring directories exist, checking prerequisites).

        Example:
            def prepare_docker_context(self):
                import os
                # Set data path for docker volume
                os.environ['TIMESCALEDB_DATA_PATH'] = str(self.data_path / 'timescaledb')
                # Ensure volume directory exists
                self.ensure_dirs(self.data_path / 'timescaledb')
        """
        pass

    def _initialize_from_data(self):  # noqa: B027 - optional hook, not abstract
        """Hook for subclasses to initialize attributes from self._data.

        Called after self._data is loaded and migrated to the current version.
        Override this in subclasses that have additional attributes
        used by to_dict().
        """
        pass

    def ensure_dirs(self, *paths: Path):
        """Ensure directory paths exist."""
        if not paths:
            paths = (self.config_path, self.data_path, self.log_path, self.cache_path)
        for path in paths:
            if not isinstance(path, Path):
                raise TypeError(f"Path {path} is not a Path object")
            path.mkdir(parents=True, exist_ok=True)

    def _initialize_default_files(self):
        """Copy default config files from package to user config directory.

        Tries two locations in order:
        1. Inside package directory (for installed packages)
        2. At project root (for development mode)
        """
        import shutil

        for filename, is_required in self.DEFAULT_FILES.items():
            dest = self.config_path / filename
            if dest.exists():
                continue

            # Try package directory first (installed package)
            src = self._paths.package_path / filename

            # If not found and we're in development mode, try project root
            if not src.exists() and self._paths.project_root:
                src = self._paths.project_root / filename

            if not src.exists():
                if is_required:
                    raise FileNotFoundError(
                        f"{filename} not found in package directory {self._paths.package_path}"
                        + (
                            f" or project root {self._paths.project_root}"
                            if self._paths.project_root
                            else ""
                        )
                    )
                continue

            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)
                print(f"Copied {filename} to {self.config_path}")
            except Exception as e:
                raise RuntimeError(f"Error copying {filename}: {e}") from e

    # NOTE: this is the Single Source of Truth for config fields
    # it defines what fields exist in the config file; save() adds __version__
    def to_dict(self) -> dict:
        """Convert config fields to dictionary, without ``__version__``."""
        return {
            "data_path": self._data_path,
            "log_path": self._log_path,
            "cache_path": self._cache_path,
        }

    def _backup(self, original: bytes) -> Path:
        """Keep the original file beside the config before it is rewritten."""
        with tempfile.NamedTemporaryFile(
            dir=self.config_path,
            prefix=f"{self.config_filename}.",
            suffix=".bak",
            delete=False,
        ) as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())
        return Path(stream.name)

    def save(self):
        """Save config to file."""
        data = {"__version__": self.__version__, **self.to_dict()}
        dump(data, self.file_path)
