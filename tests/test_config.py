# VIBE-CODED
"""
Tests for pfund_kit.config module.

Configuration is an ABC, so tests use a concrete _TestConfig subclass that
implements the abstract hooks (`_initialize_from_data`, `prepare_docker_context`)
as no-ops.
"""

from pathlib import Path

import pytest
import yaml

from pfund_kit.config import Configuration


class _TestConfig(Configuration):
    """Minimal concrete Configuration for tests."""
    def _initialize_from_data(self):
        pass

    def prepare_docker_context(self):
        pass


def _project_root(home: Path, project_name: str) -> Path:
    """The on-disk root for a given project under the new layout."""
    return home / f'.{project_name}'


@pytest.fixture
def mock_home(tmp_path, monkeypatch):
    """Redirect Path.home() to tmp_path so user paths land under ~/.{project_name}/."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))  # Windows equivalent
    return tmp_path


@pytest.fixture
def temp_package(tmp_path):
    """A package dir mimicking site-packages/<pkg>/ with default config files."""
    package_dir = tmp_path / "src" / "test_pkg"
    package_dir.mkdir(parents=True)

    logging_yml = package_dir / "logging.yml"
    logging_yml.write_text("version: 1\nloggers:\n  root:\n    level: 'WARNING'\n")

    compose_yml = package_dir / "compose.yml"
    compose_yml.write_text("version: '3'\nservices: {}\n")

    module_file = package_dir / "__init__.py"
    module_file.touch()

    return {
        'package_dir': package_dir,
        'module_file': module_file,
        'logging_yml': logging_yml,
        'compose_yml': compose_yml,
    }


@pytest.fixture
def env(mock_home, temp_package):
    """Composite fixture with everything tests need."""
    project_name = 'testproject'
    return {
        'project_name': project_name,
        'source_file': str(temp_package['module_file']),
        'home': mock_home,
        'project_root': _project_root(mock_home, project_name),
        'package': temp_package,
    }


def _write_existing_config(env: dict, payload: dict) -> Path:
    """Write a config YAML at the expected location and return its path."""
    config_dir = env['project_root'] / 'config'
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yml"
    with open(config_file, 'w') as f:
        yaml.dump(payload, f)
    return config_file


class TestConfigurationInit:
    """Test Configuration initialization scenarios."""

    def test_fresh_start_creates_config(self, env):
        config_file = env['project_root'] / 'config' / "config.yml"
        assert not config_file.exists()

        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.file_path.exists()
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == _TestConfig.__version__

    def test_fresh_start_uses_default_paths(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.data_path == env['project_root'] / 'data'
        assert config.log_path == env['project_root'] / 'logs'
        assert config.cache_path == env['project_root'] / 'cache'

    def test_fresh_start_creates_directories(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.config_path.exists()
        assert config.data_path.exists()
        assert config.log_path.exists()
        assert config.cache_path.exists()

    def test_fresh_start_copies_default_files(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.logging_config_file_path.exists()
        assert config.docker_compose_file_path.exists()
        assert 'version: 1' in config.logging_config_file_path.read_text()

    def test_loads_existing_config(self, env):
        custom_data_path = env['home'] / 'custom_data'
        custom_log_path = env['home'] / 'custom_logs'
        _write_existing_config(env, {
            '__version__': _TestConfig.__version__,
            'data_path': str(custom_data_path),
            'log_path': str(custom_log_path),
            'cache_path': str(env['project_root'] / 'cache'),
        })

        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.data_path == custom_data_path
        assert config.log_path == custom_log_path

    def test_corrupted_config_missing_version_resets(self, env, capsys):
        _write_existing_config(env, {
            'data_path': str(env['home'] / 'corrupted_data'),
            'log_path': str(env['home'] / 'corrupted_log'),
        })

        config = _TestConfig(env['project_name'], env['source_file'])

        captured = capsys.readouterr()
        assert 'corrupted or missing' in captured.out
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert '__version__' in data

    def test_config_filename_format(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.config_filename == 'config.yml'
        assert config.file_path.name == 'config.yml'


def _rename_logs_dir(data: dict) -> dict:
    """0.1.0 -> 0.2.0: `logs_dir` was renamed to `log_path`."""
    data = dict(data)
    if 'logs_dir' in data:
        data['log_path'] = data.pop('logs_dir')
    return data


def _add_marker(data: dict) -> dict:
    """0.2.0 -> 0.3.0: a subclass-owned field gains a default."""
    return {**data, 'marker': data.get('marker', 'migrated')}


class _MigratedConfig(_TestConfig):
    """Config two schema versions ahead of a 0.1.0 file."""
    __version__ = "0.3.0"
    migrations = {
        "0.1.0": ("0.2.0", _rename_logs_dir),
        "0.2.0": ("0.3.0", _add_marker),
    }

    def _initialize_from_data(self):
        self.marker = self._data.get('marker', 'fresh')

    def to_dict(self) -> dict:
        return {**super().to_dict(), 'marker': self.marker}


def _backups(env: dict) -> list[Path]:
    return sorted((env['project_root'] / 'config').glob('config.yml.*.bak'))


class TestConfigurationMigration:
    """Test configuration migration between versions."""

    def _old_payload(self, env: dict, **extra) -> dict:
        return {
            '__version__': '0.1.0',
            'data_path': str(env['project_root'] / 'data'),
            'logs_dir': str(env['project_root'] / 'logs'),
            'cache_path': str(env['project_root'] / 'cache'),
            **extra,
        }

    def test_migration_chain_updates_file_and_keeps_backup(self, env, capsys):
        config_file = _write_existing_config(env, self._old_payload(env))
        original = config_file.read_bytes()

        config = _MigratedConfig(env['project_name'], env['source_file'])

        captured = capsys.readouterr()
        assert 'Migrating config from version 0.1.0 to 0.3.0' in captured.out
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == "0.3.0"
        assert 'logs_dir' not in data
        assert data['marker'] == 'migrated'
        backups = _backups(env)
        assert len(backups) == 1
        assert backups[0].read_bytes() == original

    def test_migrated_values_are_read_by_subclass(self, env):
        # The rename must be applied before attributes are read, otherwise the
        # user's value falls back to the default and is then overwritten.
        custom_log_path = env['home'] / 'my_custom_logs'
        _write_existing_config(env, self._old_payload(env, logs_dir=str(custom_log_path)))

        config = _MigratedConfig(env['project_name'], env['source_file'])

        assert config.log_path == custom_log_path
        assert config.marker == 'migrated'
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert str(custom_log_path) in str(data['log_path'])

    def test_migration_from_intermediate_version(self, env):
        _write_existing_config(env, {
            '__version__': '0.2.0',
            'data_path': str(env['project_root'] / 'data'),
            'log_path': str(env['project_root'] / 'logs'),
            'cache_path': str(env['project_root'] / 'cache'),
            'marker': 'kept',
        })

        config = _MigratedConfig(env['project_name'], env['source_file'])

        assert config.marker == 'kept'
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == "0.3.0"

    def test_missing_migration_raises_and_leaves_file(self, env):
        config_file = _write_existing_config(env, {
            '__version__': '0.0.1',
            'data_path': str(env['project_root'] / 'data'),
            'log_path': str(env['project_root'] / 'logs'),
            'cache_path': str(env['project_root'] / 'cache'),
        })
        original = config_file.read_bytes()

        with pytest.raises(ValueError, match="No configuration migration from 0.0.1"):
            _MigratedConfig(env['project_name'], env['source_file'])

        assert config_file.read_bytes() == original
        assert not _backups(env)

    def test_migration_prevents_downgrade(self, env):
        config_file = _write_existing_config(env, {
            '__version__': '99.0',
            'data_path': str(env['project_root'] / 'data'),
            'log_path': str(env['project_root'] / 'logs'),
            'cache_path': str(env['project_root'] / 'cache'),
        })
        original = config_file.read_bytes()

        with pytest.raises(ValueError, match="newer than supported"):
            _TestConfig(env['project_name'], env['source_file'])

        assert config_file.read_bytes() == original

    def test_non_string_version_rejected(self, env):
        _write_existing_config(env, {
            '__version__': 1,
            'data_path': str(env['project_root'] / 'data'),
        })

        with pytest.raises(ValueError, match="must be a version string"):
            _TestConfig(env['project_name'], env['source_file'])

    def test_no_migration_when_version_matches(self, env, capsys):
        config_file = _write_existing_config(env, {
            '__version__': _TestConfig.__version__,
            'data_path': str(env['project_root'] / 'data'),
            'log_path': str(env['project_root'] / 'logs'),
            'cache_path': str(env['project_root'] / 'cache'),
        })
        original = config_file.read_bytes()

        _TestConfig(env['project_name'], env['source_file'])

        captured = capsys.readouterr()
        assert 'Migrating' not in captured.out
        assert config_file.read_bytes() == original
        assert not _backups(env)

    def test_corrupted_file_is_backed_up_before_reset(self, env):
        config_file = _write_existing_config(env, {
            'data_path': str(env['home'] / 'corrupted_data'),
        })
        original = config_file.read_bytes()

        _TestConfig(env['project_name'], env['source_file'])

        backups = _backups(env)
        assert len(backups) == 1
        assert backups[0].read_bytes() == original


class TestConfigurationPaths:
    """Test path management and properties."""

    def test_config_path_is_fixed(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.config_path == env['project_root'] / 'config'

    def test_path_property_returns_config_path(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.path == config.config_path

    def test_file_path_property(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.file_path == config.config_path / 'config.yml'

    def test_filename_property(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.filename == 'config.yml'

    def test_logging_config_file_path_property(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.logging_config_file_path == config.config_path / 'logging.yml'

    def test_docker_compose_file_path_property(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        assert config.docker_compose_file_path == config.config_path / 'compose.yml'

    def test_ensure_dirs_creates_all_directories(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        # __init__ calls ensure_dirs(); all four must exist.
        assert config.config_path.exists()
        assert config.data_path.exists()
        assert config.log_path.exists()
        assert config.cache_path.exists()

    def test_ensure_dirs_creates_specific_directories(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        new_path = env['home'] / 'new_subdir'
        assert not new_path.exists()

        config.ensure_dirs(new_path)

        assert new_path.exists()

    def test_ensure_dirs_validates_path_type(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        with pytest.raises(TypeError, match="not a Path object"):
            config.ensure_dirs("/some/string/path")


class TestConfigurationFileOps:
    """Test file operations (save, load, to_dict)."""

    def test_to_dict_returns_correct_schema(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        data = config.to_dict()

        assert set(data.keys()) == {'data_path', 'log_path', 'cache_path'}

    def test_to_dict_returns_path_objects(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        data = config.to_dict()

        assert isinstance(data['data_path'], Path)
        assert isinstance(data['log_path'], Path)
        assert isinstance(data['cache_path'], Path)

    def test_save_writes_to_file(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        new_data_path = env['home'] / 'modified_data'
        config.data_path = new_data_path

        config.save()

        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert str(new_data_path) in str(data['data_path'])

    def test_save_load_roundtrip(self, env):
        config1 = _TestConfig(env['project_name'], env['source_file'])
        custom_data_path = env['home'] / 'roundtrip_test'
        config1.data_path = custom_data_path
        config1.save()

        config2 = _TestConfig(env['project_name'], env['source_file'])

        assert config2.data_path == custom_data_path

    def test_save_writes_class_version(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])
        config.save()
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == _TestConfig.__version__
        assert '__version__' not in config.to_dict()


class TestConfigurationDefaultFiles:
    """Test default file initialization."""

    def test_copies_logging_yml(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.logging_config_file_path.exists()
        assert env['package']['logging_yml'].read_text() == config.logging_config_file_path.read_text()

    def test_copies_compose_yml(self, env):
        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.docker_compose_file_path.exists()
        assert env['package']['compose_yml'].read_text() == config.docker_compose_file_path.read_text()

    def test_skips_existing_default_files(self, env, capsys):
        config_path = env['project_root'] / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        existing_logging = config_path / 'logging.yml'
        custom_content = "# My custom logging config\nversion: 99\n"
        existing_logging.write_text(custom_content)

        _TestConfig(env['project_name'], env['source_file'])

        assert existing_logging.read_text() == custom_content
        captured = capsys.readouterr()
        assert 'Copied logging.yml' not in captured.out

    def test_raises_error_for_missing_source_file(self, env):
        env['package']['logging_yml'].unlink()

        with pytest.raises(FileNotFoundError, match="logging.yml not found"):
            _TestConfig(env['project_name'], env['source_file'])


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""

    def test_path_string_converted_to_path(self, env):
        config_path = env['project_root'] / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / "config.yml"

        config_content = (
            f"__version__: \"{_TestConfig.__version__}\"\n"
            f"data_path: \"{env['home'] / 'string_path'}\"\n"
            f"log_path: \"{env['home'] / 'string_path'}\"\n"
            f"cache_path: \"{env['home'] / 'string_path'}\"\n"
        )
        config_file.write_text(config_content)

        config = _TestConfig(env['project_name'], env['source_file'])

        assert isinstance(config.data_path, Path)
        assert isinstance(config.log_path, Path)
        assert isinstance(config.cache_path, Path)

    def test_multiple_instances_share_config(self, env):
        config1 = _TestConfig(env['project_name'], env['source_file'])
        custom_path = env['home'] / 'shared_test'
        config1.data_path = custom_path
        config1.save()

        config2 = _TestConfig(env['project_name'], env['source_file'])

        assert config2.data_path == custom_path

    def test_empty_config_file_treated_as_missing(self, env, capsys):
        config_path = env['project_root'] / 'config'
        config_path.mkdir(parents=True, exist_ok=True)
        config_file = config_path / "config.yml"
        config_file.write_text("")

        config = _TestConfig(env['project_name'], env['source_file'])

        captured = capsys.readouterr()
        assert 'corrupted or missing' in captured.out
        assert config.file_path.exists()
        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert '__version__' in data
        assert not _backups(env)  # nothing worth keeping

    def test_subclass_without_initialize_hook(self, env):
        class Hookless(Configuration):
            def prepare_docker_context(self):
                pass

        config = Hookless(env['project_name'], env['source_file'])
        assert config.file_path.exists()

    def test_config_with_only_version(self, env):
        _write_existing_config(env, {'__version__': _TestConfig.__version__})

        config = _TestConfig(env['project_name'], env['source_file'])

        assert config.data_path == env['project_root'] / 'data'
        assert config.log_path == env['project_root'] / 'logs'
        assert config.cache_path == env['project_root'] / 'cache'


class TestConfigurationSubclassing:
    """Test that Configuration can be properly subclassed."""

    def test_subclass_can_override_default_files(self, env):
        # Remove compose.yml from package; subclass shouldn't require it.
        env['package']['compose_yml'].unlink()

        class MinimalConfiguration(Configuration):
            DEFAULT_FILES = {Configuration.LOGGING_CONFIG_FILENAME: True}

            def _initialize_from_data(self):
                pass

            def prepare_docker_context(self):
                pass

        config = MinimalConfiguration(env['project_name'], env['source_file'])

        assert config.logging_config_file_path.exists()
        assert not config.docker_compose_file_path.exists()

    def test_subclass_can_override_version(self, env):
        class CustomConfiguration(Configuration):
            __version__ = "1.0"

            def _initialize_from_data(self):
                pass

            def prepare_docker_context(self):
                pass

        config = CustomConfiguration(env['project_name'], env['source_file'])

        with open(config.file_path) as f:
            data = yaml.safe_load(f)
        assert data['__version__'] == "1.0"
