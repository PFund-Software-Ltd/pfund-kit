from __future__ import annotations

from pathlib import Path
from abc import ABC, abstractmethod

from pfund_kit.utils.yaml import load, dump
from pfund_kit.style import cprint, TextStyle, RichColor
from pfund_kit.paths import ProjectPaths


__all__ = ['Configuration']


class Configuration(ABC):
    __version__ = "0.1"
    
    LOGGING_CONFIG_FILENAME = 'logging.yml'
    DOCKER_COMPOSE_FILENAME = 'compose.yml'

    # List of files to copy on initialization
    DEFAULT_FILES = [
        LOGGING_CONFIG_FILENAME,
        DOCKER_COMPOSE_FILENAME,
    ]
   
    def __init__(self, project_name: str, source_file: str | None = None):
        '''
        Args:
            project_name: Name of the project.
            source_file: Path to a source file for determining project layout. 
                        If None, auto-detects from the caller's __file__.
        '''
        self._paths = ProjectPaths(project_name, source_file)
            
        # fixed paths, since config_path cannot be changed
        self.config_path = self._paths.config_path
        self.config_filename = f'{self._paths.project_name.lower()}.yml'

        # load config file
        data = load(self.file_path) or {}
            
        # configurable paths
        default_data_path = self._paths.data_path
        default_log_path = self._paths.log_path
        default_cache_path = self._paths.cache_path
        self.data_path = Path(data.get('data_path', default_data_path))
        self.log_path = Path(data.get('log_path', default_log_path))
        self.cache_path = Path(data.get('cache_path', default_cache_path))

        # config file is corrupted or missing if __version__ is not present
        if '__version__' not in data:
            print(f"Config file {self.file_path} is corrupted or missing, resetting to default")
            self.save()
        else:
            existing_version = data['__version__']
            if existing_version != self.__version__:
                self._migrate(existing_data=data, existing_version=existing_version)
        
        self.ensure_dirs()
        self._initialize_default_files()
    
    @property
    def path(self):
        return self.config_path
    
    @property
    def file_path(self):
        return self.config_path / self.config_filename
    
    @property
    def filename(self):
        '''Filename of the config file.'''
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
                # Set data paths for docker volumes
                os.environ['MINIO_DATA_PATH'] = str(self.data_path / 'minio')
                os.environ['TIMESCALEDB_DATA_PATH'] = str(self.data_path / 'timescaledb')
                # Ensure volume directories exist
                self.ensure_dirs(self.data_path / 'minio', self.data_path / 'timescaledb')
        """
        pass
    
    def ensure_dirs(self, *paths: Path):
        """Ensure directory paths exist."""
        if not paths:
            paths = [self.config_path, self.data_path, self.log_path, self.cache_path]
        for path in paths:
            if not isinstance(path, Path):
                raise TypeError(f"Path {path} is not a Path object")
            path.mkdir(parents=True, exist_ok=True)
    
    def _initialize_default_files(self):
        """Copy default config files from package (e.g. site-packages) to user config directory."""
        package_path = self._paths.package_path
        
        for filename in self.DEFAULT_FILES:
            dest = self.config_path / filename
            if dest.exists():
                continue
            
            src = package_path / filename
            if not src.exists():
                raise FileNotFoundError(f"{filename} not found in package directory {package_path}")
            
            try:
                import shutil
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dest)
                print(f"Copied {filename} to {self.config_path}")
            except Exception as e:
                raise RuntimeError(f"Error copying {filename}: {e}")
    
    # NOTE: this is the Single Source of Truth for config data
    # it defines what fields exist in the config file
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            '__version__': self.__version__,
            'data_path': self.data_path,
            'log_path': self.log_path,
            'cache_path': self.cache_path,
        }
    
    def _migrate(self, existing_data: dict, existing_version: str):
        """Migrate config from old version to current version."""
        from_version = existing_version
        to_version = self.__version__
        assert float(to_version) > float(from_version), f"Cannot migrate from version {from_version} to {to_version}"
        cprint(f"Migrating config from version {from_version} to {to_version}", style=str(TextStyle.BOLD + RichColor.RED))
        
        # expected schema, what config data should be based on __version__
        expected_data = self.to_dict()
        
        # Find differences between expected schema and existing config in user's config file
        expected_keys = set(expected_data.keys())
        existing_keys = set(existing_data.keys())
        if new_keys := expected_keys - existing_keys:
            print(f"  Adding new fields: {new_keys}")
        if removed_keys := existing_keys - expected_keys:
            print(f"  Removing obsolete fields: {removed_keys}")
        
        self.save()
    
    def save(self):
        """Save config to file."""
        data = self.to_dict()
        dump(data, self.file_path)
